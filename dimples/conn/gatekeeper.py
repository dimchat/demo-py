# -*- coding: utf-8 -*-
#
#   DIM-SDK : Decentralized Instant Messaging Software Development Kit
#
#                                Written in 2019 by Moky <albert.moky@gmail.com>
#
# ==============================================================================
# MIT License
#
# Copyright (c) 2019 Albert Moky
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
import time
import traceback
from typing import Optional, Tuple

from dimsdk import ReliableMessage

from startrek.types import SocketAddress
from startrek import Channel, Hub
from startrek import BaseChannel
from startrek import Connection, ConnectionDelegate, BaseConnection
from startrek import Arrival, Departure
from startrek import Docker, DockerStatus, DockerDelegate

from tcp import StreamChannel
from tcp import ServerHub, ClientHub

from ..utils import get_remote_address, get_local_address
from ..utils import get_msg_info
from ..utils import Runner, Logging

from .protocol import DeparturePacker

from .gate import CommonGate, TCPServerGate, TCPClientGate
from .queue import MessageQueue, MessageWrapper


class StreamServerHub(ServerHub):

    def put_channel(self, channel: StreamChannel):
        self._set_channel(channel=channel, remote=channel.remote_address, local=None)

    # Override
    def _get_channel(self, remote: Optional[SocketAddress], local: Optional[SocketAddress]) -> Optional[Channel]:
        return super()._get_channel(remote=remote, local=None)

    # Override
    def _set_channel(self, channel: Channel,
                     remote: Optional[SocketAddress], local: Optional[SocketAddress]):
        super()._set_channel(channel=channel, remote=remote, local=None)

    # Override
    def _remove_channel(self, channel: Optional[Channel],
                        remote: Optional[SocketAddress], local: Optional[SocketAddress]) -> Optional[Channel]:
        return super()._remove_channel(channel=channel, remote=remote, local=None)

    # Override
    def _get_connection(self, remote: SocketAddress, local: Optional[SocketAddress]) -> Optional[Connection]:
        return super()._get_connection(remote=remote, local=None)

    # Override
    def _set_connection(self, connection: Connection,
                        remote: SocketAddress, local: Optional[SocketAddress]):
        super()._set_connection(connection=connection, remote=remote, local=None)

    # Override
    def _remove_connection(self, connection: Optional[Connection],
                           remote: SocketAddress, local: Optional[SocketAddress]) -> Optional[Connection]:
        return super()._remove_connection(connection=connection, remote=remote, local=None)


class StreamClientHub(ClientHub):

    def put_channel(self, channel: StreamChannel):
        self._set_channel(channel=channel, remote=channel.remote_address, local=None)

    # Override
    def _get_channel(self, remote: Optional[SocketAddress], local: Optional[SocketAddress]) -> Optional[Channel]:
        return super()._get_channel(remote=remote, local=None)

    # Override
    def _set_channel(self, channel: Channel,
                     remote: Optional[SocketAddress], local: Optional[SocketAddress]):
        super()._set_channel(channel=channel, remote=remote, local=None)

    # Override
    def _remove_channel(self, channel: Optional[Channel],
                        remote: Optional[SocketAddress], local: Optional[SocketAddress]) -> Optional[Channel]:
        return super()._remove_channel(channel=channel, remote=remote, local=None)

    # Override
    def _get_connection(self, remote: SocketAddress, local: Optional[SocketAddress]) -> Optional[Connection]:
        return super()._get_connection(remote=remote, local=None)

    # Override
    def _set_connection(self, connection: Connection,
                        remote: SocketAddress, local: Optional[SocketAddress]):
        super()._set_connection(connection=connection, remote=remote, local=None)

    # Override
    def _remove_connection(self, connection: Optional[Connection],
                           remote: SocketAddress, local: Optional[SocketAddress]) -> Optional[Connection]:
        return super()._remove_connection(connection=connection, remote=remote, local=None)


def reset_send_buffer_size(conn: Connection) -> bool:
    if not isinstance(conn, BaseConnection):
        print('[SOCKET] connection error: %s' % conn)
        return False
    channel = conn.channel
    if not isinstance(channel, BaseChannel):
        print('[SOCKET] channel error: %s, %s' % (channel, conn))
        return False
    sock = channel.sock
    if sock is None:
        print('[SOCKET] socket error: %s, %s' % (sock, conn))
        return False
    size = sock.getsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF)
    max_size = GateKeeper.SEND_BUFFER_SIZE
    if size < max_size:
        print('[SOCKET] change send buffer size: %d -> %d, %s' % (size, max_size, conn))
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, max_size)
        return True
    else:
        print('[SOCKET] send buffer size: %d, %s' % (size, conn))


class GateKeeper(Runner, DockerDelegate, Logging):
    """ Keep a gate to remote address """

    SEND_BUFFER_SIZE = 64 * 1024  # 64 KB

    def __init__(self, remote: Tuple[str, int], sock: Optional[socket.socket]):
        super().__init__(interval=Runner.INTERVAL_SLOW)
        self.__remote = remote
        self.__gate = self._create_gate(remote=remote, sock=sock)
        self.__queue = MessageQueue()
        self.__active = False
        self.__last_active = 0  # last update time

    def _create_gate(self, remote: Tuple[str, int], sock: Optional[socket.socket]) -> CommonGate:
        if sock is None:
            gate = TCPClientGate(delegate=self)
        else:
            gate = TCPServerGate(delegate=self)
        gate.hub = self._create_hub(delegate=gate, address=remote, sock=sock)
        return gate

    # noinspection PyMethodMayBeStatic
    def _create_hub(self, delegate: ConnectionDelegate, address: Tuple[str, int], sock: Optional[socket.socket]) -> Hub:
        if sock is None:
            # client
            assert address is not None, 'remote address empty'
            hub = StreamClientHub(delegate=delegate)
            conn = hub.connect(remote=address)
            reset_send_buffer_size(conn=conn)
            # TODO: reset send buffer size
        else:
            # server
            sock.setblocking(False)
            # sock.settimeout(0.5)
            if address is None:
                address = get_remote_address(sock=sock)
            channel = StreamChannel(sock=sock, remote=address, local=get_local_address(sock=sock))
            hub = StreamServerHub(delegate=delegate)
            hub.put_channel(channel=channel)
        return hub

    @property
    def remote_address(self) -> Tuple[str, int]:
        return self.__remote

    @property
    def gate(self) -> CommonGate:
        return self.__gate

    @property
    def active(self) -> bool:
        return self.__active

    def set_active(self, active: bool, when: float = None) -> bool:
        if when is None or when <= 0:
            when = time.time()
        elif when <= self.__last_active:
            return False
        if self.__active != active:
            self.__active = active
            self.__last_active = when
            return True

    @property  # Override
    def running(self) -> bool:
        if super().running:
            return self.gate.running

    # Override
    def stop(self):
        super().stop()
        self.gate.stop()

    # Override
    def setup(self):
        super().setup()
        self.gate.start()

    # Override
    def finish(self):
        self.gate.stop()
        super().finish()

    # Override
    def process(self) -> bool:
        gate = self.gate
        hub = gate.hub
        # from tcp import Hub
        # assert isinstance(hub, Hub), 'hub error: %s' % hub
        try:
            incoming = hub.process()
            outgoing = gate.process()
            if incoming or outgoing:
                # processed income/outgo packages
                return True
        except Exception as e:
            self.error(msg='process error: %s' % e)
            traceback.print_exc()
            return False
        if not self.active:
            # inactive, wait a while to check again
            self.__queue.purge()
            return False
        # get next message
        wrapper = self.__queue.next()
        if wrapper is None:
            # no more task now, purge failed tasks
            self.__queue.purge()
            return False
        # if msg in this wrapper is None (means sent successfully),
        # it must have been cleaned already, so it should not be empty here.
        msg = wrapper.msg
        if msg is None:
            # msg sent?
            return True
        # try to push
        ok = gate.send_ship(ship=wrapper, remote=self.remote_address, local=None)
        if not ok:
            self.error(msg='gate error, failed to send data')
        return ok

    def _docker_pack(self, payload: bytes, priority: int = 0) -> Departure:
        docker = self.gate.fetch_docker(remote=self.remote_address, local=None, advance_party=[])
        assert isinstance(docker, DeparturePacker), 'departure packer error: %s' % docker
        return docker.pack(payload=payload, priority=priority)

    def _queue_append(self, msg: ReliableMessage, ship: Departure) -> bool:
        return self.__queue.append(msg=msg, ship=ship)

    #
    #   Docker Delegate
    #

    # Override
    def docker_status_changed(self, previous: DockerStatus, current: DockerStatus, docker: Docker):
        self.info(msg='docker status changed: %s -> %s, %s' % (previous, current, docker))

    # Override
    def docker_received(self, ship: Arrival, docker: Docker):
        self.debug(msg='docker received a ship: %s, %s' % (ship, docker))

    # Override
    def docker_sent(self, ship: Departure, docker: Docker):
        # TODO: remove sent message from local cache
        pass

    # Override
    def docker_failed(self, error: IOError, ship: Departure, docker: Docker):
        self.error(msg='docker failed to send ship: %s, %s' % (ship, docker))

    # Override
    def docker_error(self, error: IOError, ship: Departure, docker: Docker):
        self.error(msg='docker error while sending ship: %s, %s' % (ship, docker))
        if isinstance(ship, MessageWrapper):
            msg = ship.msg
            if msg is not None:
                self.error(msg='error message: %s' % get_msg_info(msg=msg))
