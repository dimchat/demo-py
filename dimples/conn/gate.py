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
from abc import ABC
from typing import Generic, TypeVar, Optional, Union

from startrek.types import SocketAddress
from startrek.net.state import StateOrder
from startrek import Hub
from startrek import Connection, ConnectionState, ActiveConnection
from startrek import Porter, PorterStatus, PorterDelegate
from startrek import Arrival, StarGate

from ..utils import Logging

from .mtp import TransactionID, MTPStreamPorter, MTPHelper
from .mars import MarsStreamArrival, MarsStreamPorter, MarsHelper
from .ws import WSPorter
from .flexible import FlexiblePorter


H = TypeVar('H')


# noinspection PyAbstractClass
class CommonGate(StarGate, Logging, Generic[H], ABC):

    def __init__(self, delegate: PorterDelegate):
        super().__init__(delegate=delegate)
        self.__hub: H = None

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
    def _get_porter(self, remote: SocketAddress, local: Optional[SocketAddress]) -> Optional[Porter]:
        return super()._get_porter(remote=remote, local=None)

    # Override
    def _set_porter(self, porter: Porter,
                    remote: SocketAddress, local: Optional[SocketAddress]) -> Optional[Porter]:
        return super()._set_porter(porter=porter, remote=remote, local=None)

    # Override
    def _remove_porter(self, porter: Optional[Porter],
                       remote: SocketAddress, local: Optional[SocketAddress]) -> Optional[Porter]:
        return super()._remove_porter(porter=porter, remote=remote, local=None)

    def get_porter_status(self, remote: SocketAddress, local: Optional[SocketAddress]) -> Optional[PorterStatus]:
        docker = self._get_porter(remote=remote, local=local)
        if docker is None:
            return None
        else:
            return docker.status

    async def fetch_porter(self, remote: SocketAddress, local: Optional[SocketAddress]) -> Optional[Porter]:
        # get connection from hub
        hub = self.hub
        assert isinstance(hub, Hub), 'gate hub error: %s' % hub
        conn = await hub.connect(remote=remote, local=local)
        if conn is not None:
            # connected, get docker with this connection
            return await self._dock(connection=conn, new_porter=True)
        assert False, 'failed to get connection: %s -> %s' % (local, remote)

    async def send_response(self, payload: bytes, ship: Arrival,
                            remote: SocketAddress, local: Optional[SocketAddress]) -> bool:
        worker = self._get_porter(remote=remote, local=local)
        if isinstance(worker, FlexiblePorter):
            return await worker.send_data(payload=payload)
        elif isinstance(worker, MTPStreamPorter):
            # sn = TransactionID.from_data(data=ship.sn)
            sn = TransactionID.generate()
            pack = MTPHelper.create_message(body=payload, sn=sn)
            return await worker.send_package(pack=pack)
        elif isinstance(worker, MarsStreamPorter):
            assert isinstance(ship, MarsStreamArrival), 'responding ship error: %s' % ship
            mars = MarsHelper.create_respond(head=ship.package.head, payload=payload)
            ship = MarsStreamPorter.create_departure(mars=mars)
            return await worker.send_ship(ship=ship)
        elif isinstance(worker, WSPorter):
            ship = worker.pack(payload=payload, priority=1, needs_respond=False)
            return await worker.send_ship(ship=ship)
        else:
            raise LookupError('docker error (%s, %s): %s' % (remote, local, worker))

    # Override
    async def _heartbeat(self, connection: Connection):
        # let the client to do the job
        if isinstance(connection, ActiveConnection):
            await super()._heartbeat(connection=connection)

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


#
#   Server Gates
#


class TCPServerGate(CommonGate, Generic[H]):

    # Override
    def _create_porter(self, remote: SocketAddress, local: Optional[SocketAddress]) -> Porter:
        docker = FlexiblePorter(remote=remote, local=local)
        docker.delegate = self.delegate
        return docker


class UDPServerGate(CommonGate, Generic[H]):

    # Override
    def _create_porter(self, remote: SocketAddress, local: Optional[SocketAddress]) -> Porter:
        docker = MTPStreamPorter(remote=remote, local=local)
        docker.delegate = self.delegate
        return docker


#
#   Client Gates
#


class TCPClientGate(CommonGate, Generic[H]):

    # Override
    def _create_porter(self, remote: SocketAddress, local: Optional[SocketAddress]) -> Porter:
        docker = MTPStreamPorter(remote=remote, local=local)
        docker.delegate = self.delegate
        return docker


class UDPClientGate(CommonGate, Generic[H]):

    # Override
    def _create_porter(self, remote: SocketAddress, local: Optional[SocketAddress]) -> Porter:
        docker = MTPStreamPorter(remote=remote, local=local)
        docker.delegate = self.delegate
        return docker
