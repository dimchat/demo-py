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

import socket
import threading
from abc import ABC
from typing import Generic, TypeVar, Optional, Union, List

from startrek.types import SocketAddress
from startrek.net.state import StateOrder
from startrek import Hub, Channel
from startrek import Connection, ConnectionState, BaseConnection, ActiveConnection
from startrek import Docker, DockerDelegate
from startrek import Arrival, StarDocker, StarGate

from ..utils import Logging

from .mtp import TransactionID, MTPStreamDocker, MTPHelper
from .mars import MarsStreamArrival, MarsStreamDocker, MarsHelper
from .ws import WSDocker


H = TypeVar('H')


# noinspection PyAbstractClass
class CommonGate(StarGate, Logging, Generic[H], ABC):

    def __init__(self, delegate: DockerDelegate):
        super().__init__(delegate=delegate)
        self.__hub: H = None
        self.__lock = threading.Lock()

    @property
    def hub(self) -> H:
        return self.__hub

    @hub.setter
    def hub(self, h: H):
        self.__hub = h

    #
    #   Docker
    #

    # Override
    def _get_docker(self, remote: SocketAddress, local: Optional[SocketAddress]) -> Optional[Docker]:
        return super()._get_docker(remote=remote, local=None)

    # Override
    def _set_docker(self, docker: Docker,
                    remote: SocketAddress, local: Optional[SocketAddress]) -> Optional[Docker]:
        return super()._set_docker(docker=docker, remote=remote, local=None)

    # Override
    def _remove_docker(self, docker: Optional[Docker],
                       remote: SocketAddress, local: Optional[SocketAddress]) -> Optional[Docker]:
        return super()._remove_docker(docker=docker, remote=remote, local=None)

    async def fetch_docker(self, advance_party: List[bytes],
                           remote: SocketAddress, local: Optional[SocketAddress]) -> Docker:
        # try to get docker
        with self.__lock:
            old = self._get_docker(remote=remote, local=local)
            if old is None:  # and advance_party is not None:
                # create & cache docker
                worker = self._create_docker(advance_party, remote=remote, local=local)
                self._set_docker(worker, remote=remote, local=local)
            else:
                worker = old
        if old is None:
            hub = self.hub
            assert isinstance(hub, Hub), 'gate hub error: %s' % hub
            conn = await hub.connect(remote=remote, local=local)
            if conn is None:
                # assert False, 'failed to get connection: %s -> %s' % (local, remote)
                self._remove_docker(worker, remote=remote, local=local)
                worker = None
            else:
                assert isinstance(worker, StarDocker), 'docker error: %s, %s' % (remote, worker)
                # set connection for this docker
                await worker.set_connection(conn)
        return worker

    async def send_response(self, payload: bytes, ship: Arrival,
                            remote: SocketAddress, local: Optional[SocketAddress]) -> bool:
        worker = self._get_docker(remote=remote, local=local)
        if isinstance(worker, MTPStreamDocker):
            # sn = TransactionID.from_data(data=ship.sn)
            sn = TransactionID.generate()
            pack = MTPHelper.create_message(body=payload, sn=sn)
            return await worker.send_package(pack=pack)
        elif isinstance(worker, MarsStreamDocker):
            assert isinstance(ship, MarsStreamArrival), 'responding ship error: %s' % ship
            mars = MarsHelper.create_respond(head=ship.package.head, payload=payload)
            ship = MarsStreamDocker.create_departure(mars=mars)
            return await worker.send_ship(ship=ship)
        elif isinstance(worker, WSDocker):
            ship = worker.pack(payload=payload)
            return await worker.send_ship(ship=ship)
        else:
            raise LookupError('docker error (%s, %s): %s' % (remote, local, worker))

    # Override
    async def _heartbeat(self, connection: Connection):
        # let the client to do the job
        if isinstance(connection, ActiveConnection):
            await super()._heartbeat(connection=connection)

    # Override
    def _cache_advance_party(self, data: bytes, connection: Connection) -> List[bytes]:
        # TODO: cache the advance party before decide which docker to use
        if len(data) == 0:
            return []
        else:
            return [data]

    # Override
    def _clear_advance_party(self, connection: Connection):
        # TODO: remove advance party for this connection
        pass

    #
    #   Connection Delegate
    #

    # Override
    async def connection_state_changed(self, previous: Optional[ConnectionState], current: Optional[ConnectionState],
                                       connection: Connection):
        index = -1 if current is None else current.index
        if index == StateOrder.ERROR:
            self.error(msg='connection lost: %s -> %s, %s' % (previous, current, connection.remote_address))
        elif index != StateOrder.EXPIRED and index != StateOrder.MAINTAINING:
            self.debug(msg='connection state changed: %s -> %s, %s' % (previous, current, connection.remote_address))
        try:
            await super().connection_state_changed(previous=previous, current=current, connection=connection)
        except AssertionError as error:
            self.error(msg='connection callback failed: %s' % error)

    # Override
    async def connection_received(self, data: bytes, connection: Connection):
        self.debug(msg='received %d byte(s): %s' % (len(data), connection.remote_address))
        await super().connection_received(data=data, connection=connection)

    # Override
    async def connection_sent(self, sent: int, data: bytes, connection: Connection):
        await super().connection_sent(sent=sent, data=data, connection=connection)
        self.debug(msg='sent %d byte(s): %s' % (len(data), connection.remote_address))

    # Override
    async def connection_failed(self, error: Union[IOError, socket.error], data: bytes, connection: Connection):
        await super().connection_failed(error=error, data=data, connection=connection)
        self.error(msg='failed to send %d byte(s): %s, remote=%s' % (len(data), error, connection.remote_address))

    # Override
    async def connection_error(self, error: Union[IOError, socket.error], connection: Connection):
        await super().connection_error(error=error, connection=connection)
        if error is not None and str(error).startswith('failed to send: '):
            self.warning(msg='ignore socket error: %s, remote=%s' % (error, connection.remote_address))

    def get_channel(self, remote: Optional[SocketAddress], local: Optional[SocketAddress]) -> Optional[Channel]:
        docker = self._get_docker(remote=remote, local=local)
        if isinstance(docker, StarDocker):
            conn = docker.connection
            if isinstance(conn, BaseConnection):
                return conn.channel


#
#   Server Gates
#


class TCPServerGate(CommonGate, Generic[H]):

    # Override
    def _create_docker(self, parties: List[bytes],
                       remote: SocketAddress, local: Optional[SocketAddress]) -> Docker:
        count = len(parties)
        if count == 0:
            # return MTPStreamDocker(remote=remote, local=local, gate=self)
            assert False, 'data empty: %s -> %s' % (remote, local)
        data = parties[0]
        for i in range(1, count):
            data = data + parties[i]
        if len(data) == 0:
            assert False, 'data empty: %s -> %s' % (remote, local)
        # check data format before creating docker
        if MTPStreamDocker.check(data=data):
            docker = MTPStreamDocker(remote=remote, local=local)
        elif MarsStreamDocker.check(data=data):
            docker = MarsStreamDocker(remote=remote, local=local)
        elif WSDocker.check(data=data):
            docker = WSDocker(remote=remote, local=local)
        else:
            raise LookupError('failed to create docker: %s' % data)
        docker.delegate = self.delegate
        return docker


class UDPServerGate(CommonGate, Generic[H]):

    # Override
    def _create_docker(self, parties: List[bytes],
                       remote: SocketAddress, local: Optional[SocketAddress]) -> Docker:
        count = len(parties)
        if count == 0:
            # return MTPStreamDocker(remote=remote, local=local, gate=self)
            assert False, 'data empty: %s -> %s' % (remote, local)
        data = parties[count - 1]
        # check data format before creating docker
        if MTPStreamDocker.check(data=data):
            docker = MTPStreamDocker(remote=remote, local=local)
        else:
            raise LookupError('failed to create docker: %s' % data)
        docker.delegate = self.delegate
        return docker


#
#   Client Gates
#


class TCPClientGate(CommonGate, Generic[H]):

    # Override
    def _create_docker(self, parties: List[bytes],
                       remote: SocketAddress, local: Optional[SocketAddress]) -> Docker:
        docker = MTPStreamDocker(remote=remote, local=local)
        docker.delegate = self.delegate
        return docker


class UDPClientGate(CommonGate, Generic[H]):

    # Override
    def _create_docker(self, parties: List[bytes],
                       remote: SocketAddress, local: Optional[SocketAddress]) -> Docker:
        docker = MTPStreamDocker(remote=remote, local=local)
        docker.delegate = self.delegate
        return docker
