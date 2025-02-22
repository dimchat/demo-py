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
from typing import Optional, List, Tuple

from startrek.types import SocketAddress
from startrek import Arrival, ArrivalShip
from startrek import Departure, DepartureShip, DeparturePriority

from udp.ba import Data
from tcp import PlainPorter

from ..utils import utf8_encode, utf8_decode, base64_encode, base64_decode

from .protocol import NetMsg, NetMsgHead, NetMsgSeq
from .protocol import DeparturePacker
from .seeker import MarsPackageSeeker


def encode_sn(sn: bytes) -> bytes:
    """ Encode to Base-64 """
    return utf8_encode(string=base64_encode(data=sn))


def decode_sn(sn: bytes) -> bytes:
    """ Decode from Base-64 """
    return base64_decode(string=utf8_decode(data=sn))


def seq_to_sn(seq: int) -> bytes:
    return seq.to_bytes(length=4, byteorder='big')


def fetch_sn(body: bytes) -> Optional[bytes]:
    if body is not None and body.startswith(b'Mars SN:'):
        pos = body.find(b'\n', 8)
        assert pos > 8, 'Mars SN error: %s' % body
        return body[8:pos]


def get_sn(mars: NetMsg) -> bytes:
    sn = fetch_sn(body=mars.body)
    if sn is None:
        sn = seq_to_sn(seq=mars.head.seq)
    else:
        sn = decode_sn(sn=sn)
    return sn


class MarsHelper:

    seeker = MarsPackageSeeker()

    @classmethod
    def seek_header(cls, data: bytes) -> Tuple[Optional[NetMsgHead], int]:
        data = Data(buffer=data)
        return cls.seeker.seek_header(data=data)

    @classmethod
    def seek_package(cls, data: bytes) -> Tuple[Optional[NetMsg], int]:
        data = Data(buffer=data)
        return cls.seeker.seek_package(data=data)

    @classmethod
    def create_respond(cls, head: NetMsgHead, payload: bytes) -> NetMsg:
        """ create for SEND_MSG, NOOP """
        cmd = head.cmd
        seq = head.seq
        assert cmd in [NetMsgHead.SEND_MSG, NetMsgHead.NOOP], 'cmd error: %s' % cmd
        body = payload
        head = NetMsgHead.new(cmd=cmd, seq=seq, body_len=len(body))
        return NetMsg.new(head=head, body=body)

    @classmethod
    def create_push(cls, payload: bytes) -> NetMsg:
        """ create for PUSH_MESSAGE """
        seq = NetMsgSeq.generate()
        sn = seq_to_sn(seq=seq)
        sn = encode_sn(sn=sn)
        # pack 'sn + payload'
        body = b'Mars SN:' + sn + b'\n' + payload
        head = NetMsgHead.new(cmd=NetMsgHead.PUSH_MESSAGE, body_len=len(body))
        return NetMsg.new(head=head, body=body)


class MarsStreamArrival(ArrivalShip):
    """ Mars Stream Arrival Ship """

    def __init__(self, mars: NetMsg, now: float = 0):
        super().__init__(now=now)
        self.__mars = mars
        self.__sn = get_sn(mars=self.__mars)

    @property
    def package(self) -> NetMsg:
        return self.__mars

    @property
    def payload(self) -> Optional[bytes]:
        body = self.__mars.body
        sn = fetch_sn(body=body)
        if sn is None:
            return body
        else:
            # pos = body.find(b'\n')
            # return body[pos+1:]
            skip = 8 + len(sn) + 1
            return body[skip:]

    @property  # Override
    def sn(self) -> bytes:
        return self.__sn

    # Override
    def assemble(self, ship):
        assert self is ship, 'mars arrival error: %s, %s' % (ship, self)
        return ship


class MarsStreamDeparture(DepartureShip):
    """ Mars Stream Departure Ship """

    def __init__(self, mars: NetMsg, priority: int = 0, max_tries: int = 3):
        super().__init__(priority=priority, max_tries=max_tries)
        self.__mars = mars
        self.__sn = get_sn(mars=mars)
        self.__fragments = [mars.data]

    @property
    def package(self) -> NetMsg:
        return self.__mars

    @property  # Override
    def sn(self) -> bytes:
        return self.__sn

    @property  # Override
    def fragments(self) -> List[bytes]:
        return self.__fragments

    # Override
    def check_response(self, ship: Arrival) -> bool:
        # assert isinstance(ship, MarsStreamArrival), 'arrival ship error: %s' % ship
        assert ship.sn == self.sn, 'SN not match: %s, %s' % (ship.sn, self.sn)
        self.__fragments.clear()
        return True

    @property
    def is_important(self) -> bool:
        # 'PUSH_MESSAGE' needs response
        mars = self.package
        return mars.head.cmd == NetMsgHead.PUSH_MESSAGE


class MarsStreamPorter(PlainPorter, DeparturePacker):
    """ Docker for Mars packages """

    def __init__(self, remote: SocketAddress, local: Optional[SocketAddress]):
        super().__init__(remote=remote, local=local)
        self.__chunks = b''
        self.__chunks_lock = threading.RLock()
        self.__package_received = False

    def _parse_package(self, data: bytes) -> Tuple[Optional[NetMsg], int]:
        with self.__chunks_lock:
            # join the data to the memory cache
            data = self.__chunks + data
            self.__chunks = b''
            # try to fetch a package
            pack, offset = MarsHelper.seek_package(data=data)
            self.__package_received = pack is not None
            remain_len = len(data)
            if offset >= 0:
                # 'error part' + 'mars package' + 'remaining data
                if pack is not None:
                    offset += pack.length
                if offset == 0:
                    self.__chunks = data + self.__chunks
                elif offset < remain_len:
                    data = data[offset:]
                    self.__chunks = data + self.__chunks
                remain_len -= offset
            return pack, remain_len

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
    def _get_arrivals(self, data: bytes) -> List[Arrival]:
        ships = []
        while True:
            pack, remain_len = self._parse_package(data=data)
            if pack is None:
                # waiting for more data
                break
            # if pack.body is None:
            #     continue
            ships.append(MarsStreamArrival(mars=pack))
            if remain_len > 0:
                # continue to check the tail
                data = b''
            else:
                # all data processed
                break
        return ships

    # Override
    async def _check_arrival(self, ship: Arrival) -> Optional[Arrival]:
        assert isinstance(ship, MarsStreamArrival), 'arrival ship error: %s' % ship
        payload = ship.payload
        if payload is None:
            body_len = 0
        else:
            body_len = len(payload)
        mars = ship.package
        head = mars.head
        # 0. check body length
        if head.body_length != mars.body_length:
            # sticky data?
            print('[Mars] package not completed: body_len=%d, %s' % (body_len, mars))
            return ship
        # 1. check head cmd
        cmd = head.cmd
        if cmd == NetMsgHead.SEND_MSG:
            # handle SEND_MSG request
            if mars.body is None:
                # FIXME: should not happen
                return None
        elif cmd == NetMsgHead.NOOP:
            # handle NOOP request
            if body_len == 0 or payload == NOOP:
                ship = self.create_departure(mars=mars, priority=DeparturePriority.SLOWER)
                await self.send_ship(ship=ship)
                return None
        # 2. check body
        if body_len == 4:
            if payload == PING:
                mars = MarsHelper.create_respond(head=head, payload=PONG)
                ship = self.create_departure(mars=mars, priority=DeparturePriority.SLOWER)
                await self.send_ship(ship=ship)
                return None
            elif payload == PONG:
                # FIXME: client should not sent 'PONG' to server
                return None
            elif payload == NOOP:
                # FIXME: 'NOOP' can only sent by NOOP cmd
                return None
        # 3. check for response
        await self._check_response(ship=ship)
        # NOTICE: the delegate must respond mars package with same cmd & seq,
        #         otherwise the connection will be closed by client
        return ship

    # Override
    async def heartbeat(self):
        # heartbeat by client
        pass

    # Override
    def pack(self, payload: bytes, priority: int, needs_respond: bool) -> Optional[Departure]:
        mars = MarsHelper.create_push(payload=payload)
        return self.create_departure(mars=mars, priority=priority)

    @classmethod
    def create_departure(cls, mars: NetMsg, priority: int = 0) -> Departure:
        cmd = mars.head.cmd
        if cmd == NetMsgHead.PUSH_MESSAGE:
            # 'PUSH_MESSAGE' needs response
            return MarsStreamDeparture(mars=mars, priority=priority)
        else:
            # others will be removed immediately after sent
            return MarsStreamDeparture(mars=mars, priority=priority, max_tries=1)

    @classmethod
    def check(cls, data: bytes) -> bool:
        head, offset = MarsHelper.seek_header(data=data)
        return head is not None


#
#  const
#

PING = b'PING'
PONG = b'PONG'
NOOP = b'NOOP'
OK = b'OK'
