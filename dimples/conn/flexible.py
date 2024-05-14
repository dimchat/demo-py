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

from typing import Optional, Union, List

from startrek.types import SocketAddress
from startrek import Connection
from startrek import Arrival, Departure
from startrek import StarDocker

from .ws import WSDocker
from .mtp import MTPStreamDocker
from .mars import MarsStreamDocker


class FlexibleDocker(StarDocker):

    def __init__(self, remote: SocketAddress, local: Optional[SocketAddress]):
        super().__init__(remote=remote, local=local)
        self.__docker: Optional[StarDocker] = None

    def _get_docker(self, data: bytes) -> Optional[StarDocker]:
        docker = self.__docker
        if docker is not None or len(data) == 0:
            return docker
        # check data for packer
        if WSDocker.check(data=data):
            docker = WSDocker(remote=self.remote_address, local=self.local_address)
        elif MTPStreamDocker.check(data=data):
            docker = MTPStreamDocker(remote=self.remote_address, local=self.local_address)
        elif MarsStreamDocker.check(data=data):
            docker = MarsStreamDocker(remote=self.remote_address, local=self.local_address)
        else:
            print('[FlexibleDocker] unsupported data format: %s' % data)
            return None
        # OK
        docker.delegate = self.delegate
        docker.set_connection(conn=self.connection)
        self.__docker = docker
        return docker

    # Override
    async def set_connection(self, conn: Optional[Connection]):
        await super().set_connection(conn=conn)
        docker = self.__docker
        if docker is not None:
            await docker.set_connection(conn=conn)

    # Override
    async def send_ship(self, ship: Departure) -> bool:
        docker = self.__docker
        if docker is not None:
            return await docker.send_ship(ship=ship)

    # Override
    async def process_received(self, data: bytes):
        docker = self._get_docker(data=data)
        if docker is not None:
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
        cnt = self.__dock.purge(now=now)
        docker = self.__docker
        if docker is not None:
            cnt += docker.purge(now=now)
        return cnt

    # Override
    async def close(self):
        await self.set_connection(conn=None)
        docker = self.__docker
        if docker is not None:
            self.__docker = None
            await docker.close()

    # Override
    async def process(self) -> bool:
        docker = self.__docker
        if docker is not None:
            return await docker.process()

    # Override
    async def send_data(self, payload: Union[bytes, bytearray]) -> bool:
        docker = self.__docker
        if docker is not None:
            return await docker.send_data(payload=payload)

    # Override
    async def heartbeat(self):
        docker = self.__docker
        if docker is not None:
            await docker.heartbeat()
