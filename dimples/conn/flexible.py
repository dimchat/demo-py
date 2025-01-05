# -*- coding: utf-8 -*-
#
#   Star Gate: Interfaces for network connection
#
#                                Written in 2024 by Moky <albert.moky@gmail.com>
#
# ==============================================================================
# MIT License
#
# Copyright (c) 2024 Albert Moky
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

from typing import Optional, List

from startrek.types import SocketAddress
from startrek.skywalker import Runner
from startrek import Connection
from startrek import Arrival, Departure
from startrek import StarPorter

from ..utils import Logging
from .protocol import DeparturePacker

from .ws import WSPorter
from .mtp import MTPStreamPorter, TransactionID, MTPHelper
from .mars import MarsStreamPorter, MarsHelper


class FlexiblePorter(StarPorter, DeparturePacker, Logging):

    def __init__(self, remote: SocketAddress, local: Optional[SocketAddress]):
        super().__init__(remote=remote, local=local)
        self.__porter: Optional[StarPorter] = None

    # Override
    async def set_connection(self, conn: Optional[Connection]):
        await super().set_connection(conn=conn)
        docker = self.__porter
        if docker is None:
            self.error(msg='docker not ready, failed to set connection: %s' % conn)
        else:
            await docker.set_connection(conn=conn)

    # Override
    async def send_ship(self, ship: Departure) -> bool:
        docker = self.__porter
        if docker is None:
            self.error(msg='docker not ready, failed to send ship: %s' % ship)
            return False
        else:
            return await docker.send_ship(ship=ship)

    # Override
    async def process_received(self, data: bytes):
        docker = self.__porter
        if docker is None:
            # check data for packer
            if WSPorter.check(data=data):
                docker = WSPorter(remote=self.remote_address, local=self.local_address)
            elif MTPStreamPorter.check(data=data):
                docker = MTPStreamPorter(remote=self.remote_address, local=self.local_address)
            elif MarsStreamPorter.check(data=data):
                docker = MarsStreamPorter(remote=self.remote_address, local=self.local_address)
            else:
                self.error(msg='unsupported data format: %s' % data)
                return None
            # initialize
            docker.delegate = self.delegate
            coro = docker.set_connection(conn=self.connection)
            Runner.async_task(coro=coro)
            self.__porter = docker
        # OK
        return await docker.process_received(data=data)

    # Override
    def _get_arrivals(self, data: bytes) -> List[Arrival]:
        raise AssertionError('should not happen')

    # Override
    async def _check_arrival(self, ship: Arrival) -> Optional[Arrival]:
        raise AssertionError('should not happen')

    # Override
    async def _check_response(self, ship: Arrival) -> Optional[Departure]:
        raise AssertionError('should not happen')

    # Override
    def _assemble_arrival(self, ship: Arrival) -> Optional[Arrival]:
        raise AssertionError('should not happen')

    # Override
    def _next_departure(self, now: float) -> Optional[Departure]:
        raise AssertionError('should not happen')

    # Override
    def purge(self, now: float = 0) -> int:
        cnt = super().purge(now=now)
        docker = self.__porter
        if docker is None:
            self.debug(msg='docker not ready, failed to purge')
        else:
            cnt += docker.purge(now=now)
        return cnt

    # Override
    async def close(self):
        await super().set_connection(conn=None)
        docker = self.__porter
        if docker is None:
            self.warning(msg='docker not ready, failed to close')
        else:
            self.__porter = None
            await docker.close()

    # Override
    async def process(self) -> bool:
        docker = self.__porter
        if docker is None:
            self.debug(msg='docker not ready, failed to process')
            return False
        else:
            return await docker.process()

    # Override
    async def send_data(self, payload: bytes) -> bool:
        docker = self.__porter
        if docker is None:
            self.error(msg='docker not ready, failed to send payload: %s' % payload)
            return False
        elif isinstance(docker, WSPorter):
            ship = docker.pack(payload=payload, priority=0, needs_respond=True)
            return await docker.send_ship(ship=ship)
        elif isinstance(docker, MTPStreamPorter):
            # sn = TransactionID.from_data(data=ship.sn)
            sn = TransactionID.generate()
            pack = MTPHelper.create_message(body=payload, sn=sn)
            return await docker.send_package(pack=pack)
        elif isinstance(docker, MarsStreamPorter):
            mars = MarsHelper.create_push(payload=payload)
            ship = MarsStreamPorter.create_departure(mars=mars)
            return await docker.send_ship(ship=ship)
        else:
            # error
            return await docker.send_data(payload=payload)

    # Override
    async def heartbeat(self):
        docker = self.__porter
        if docker is None:
            self.warning(msg='docker not ready, failed to heart bet')
        else:
            await docker.heartbeat()

    # Override
    def pack(self, payload: bytes, priority: int, needs_respond: bool) -> Optional[Departure]:
        docker = self.__porter
        if docker is None:
            self.error(msg='docker not ready, failed to pack: %s' % payload)
            return None
        else:
            assert isinstance(docker, DeparturePacker), 'docker error: %s' % docker
        return docker.pack(payload=payload, priority=priority, needs_respond=needs_respond)
