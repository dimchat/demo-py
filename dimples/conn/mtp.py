# -*- coding: utf-8 -*-
#
#   Star Gate: Interfaces for network connection
#
#                                Written in 2021 by Moky <albert.moky@gmail.com>
#
# ==============================================================================
# MIT License
#
# Copyright (c) 2021 Albert Moky
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.
# ==============================================================================

import threading
from typing import Optional, Union, List, Tuple

from startrek import Arrival, Departure
from startrek.types import SocketAddress

from udp.ba import ByteArray, Data
from udp.mtp import DataType, TransactionID, Header, Package
from udp import PackageArrival, PackageDeparture, PackagePorter

from .protocol import DeparturePacker
from .seeker import MTPPackageSeeker


class MTPHelper:

    seeker = MTPPackageSeeker()

    @classmethod
    def seek_header(cls, data: ByteArray) -> Tuple[Optional[Header], int]:
        return cls.seeker.seek_header(data=data)

    @classmethod
    def seek_package(cls, data: ByteArray) -> Tuple[Optional[Package], int]:
        return cls.seeker.seek_package(data=data)

    @classmethod
    def create_command(cls, body: Union[bytes, ByteArray]) -> Package:
        if not isinstance(body, ByteArray):
            body = Data(buffer=body)
        return Package.new(data_type=DataType.COMMAND,
                           body_length=body.size, body=body)

    @classmethod
    def create_message(cls, body: Union[bytes, ByteArray], sn: Optional[TransactionID] = None) -> Package:
        if not isinstance(body, ByteArray):
            body = Data(buffer=body)
        return Package.new(data_type=DataType.MESSAGE, sn=sn, body_length=body.size, body=body)

    @classmethod
    def respond_command(cls, sn: TransactionID, body: Union[bytes, ByteArray]) -> Package:
        if not isinstance(body, ByteArray):
            body = Data(buffer=body)
        return Package.new(data_type=DataType.COMMAND_RESPONSE,
                           sn=sn, body_length=body.size, body=body)

    @classmethod
    def respond_message(cls, sn: TransactionID, pages: int, index: int, body: Union[bytes, ByteArray]) -> Package:
        if not isinstance(body, ByteArray):
            body = Data(buffer=body)
        return Package.new(data_type=DataType.MESSAGE_RESPONSE,
                           sn=sn, pages=pages, index=index, body_length=body.size, body=body)


class MTPStreamArrival(PackageArrival):
    """ MTP Stream Arrival Ship """

    @property
    def payload(self) -> Optional[bytes]:
        pack = self.package
        if pack is not None:
            body = pack.body
            if body is not None:
                return body.get_bytes()


class MTPStreamDeparture(PackageDeparture):
    """ MTP Stream Departure Ship """

    # Override
    def _split_package(self, pack: Package) -> List[Package]:
        # stream docker will not separate packages
        return [pack]


class MTPStreamPorter(PackagePorter, DeparturePacker):
    """ Docker for MTP packages """

    def __init__(self, remote: SocketAddress, local: Optional[SocketAddress]):
        super().__init__(remote=remote, local=local)
        self.__chunks = Data.ZERO
        self.__chunks_lock = threading.RLock()
        self.__package_received = False

    # Override
    def _parse_package(self, data: bytes) -> Optional[Package]:
        with self.__chunks_lock:
            # join the data to the memory cache
            data = self.__chunks.concat(data)
            self.__chunks = Data.ZERO
            # try to fetch a package
            pack, offset = MTPHelper.seek_package(data=data)
            self.__package_received = pack is not None
            remain_len = len(data)
            if offset >= 0:
                # 'error part' + 'MTP package' + 'remaining data
                if pack is not None:
                    offset += pack.size
                if offset == 0:
                    self.__chunks = data.concat(self.__chunks)
                elif offset < data.size:
                    data = data.slice(start=offset)
                    self.__chunks = data.concat(self.__chunks)
                remain_len -= offset
            return pack

    # Override
    async def process_received(self, data: bytes):
        # the cached data maybe contain sticky packages,
        # so we need to process them circularly here
        self.__package_received = True
        while self.__package_received:
            self.__package_received = False
            await super().process_received(data=data)
            data = b''

    # Override
    async def _check_arrival(self, ship: Arrival) -> Optional[Arrival]:
        assert isinstance(ship, MTPStreamArrival), 'arrival ship error: %s' % ship
        pack = ship.package
        if pack is None:
            fragments = ship.fragments
            count = len(fragments)
            assert count > 0, 'fragments empty: %s' % ship
            pack = fragments[count - 1]
        head = pack.head
        # check body length
        if head.body_length != pack.body.size:
            # sticky data?
            print('[MTP] package not completed: body_len=%d, %s' % (pack.body.size, pack))
            return ship
        # check for response
        return await super()._check_arrival(ship=ship)

    # Override
    def _create_arrival(self, pack: Package) -> Arrival:
        return MTPStreamArrival(pack=pack)

    # Override
    def _create_departure(self, pack: Package, priority: int = 0) -> Departure:
        if pack.is_message:
            # normal package
            return MTPStreamDeparture(pack=pack, priority=priority)
        else:
            # response package needs no response again,
            # so this ship will be removed immediately after sent.
            return MTPStreamDeparture(pack=pack, priority=priority, max_tries=1)

    #
    #   Packing
    #

    # Override
    def _create_command(self, body: Union[bytes, bytearray]) -> Package:
        return MTPHelper.create_command(body=body)

    # Override
    def _create_message(self, body: Union[bytes, bytearray]) -> Package:
        return MTPHelper.create_message(body=body)

    # Override
    def _create_command_response(self, sn: TransactionID, body: bytes) -> Package:
        return MTPHelper.respond_command(sn=sn, body=body)

    # Override
    def _create_message_response(self, sn: TransactionID, pages: int, index: int) -> Package:
        return MTPHelper.respond_message(sn=sn, pages=pages, index=index, body=OK)

    # Override
    def pack(self, payload: bytes, priority: int, needs_respond: bool) -> Optional[Departure]:
        pkg = MTPHelper.create_message(body=payload)
        return self._create_departure(pack=pkg, priority=priority)

    @classmethod
    def check(cls, data: bytes) -> bool:
        head, offset = MTPHelper.seek_header(data=Data(buffer=data))
        return head is not None


#
#  const
#

PING = b'PING'
PONG = b'PONG'
NOOP = b'NOOP'
OK = b'OK'
AGAIN = b'AGAIN'
