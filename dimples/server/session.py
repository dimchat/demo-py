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

"""
    Session Server
    ~~~~~~~~~~~~~~

    for login user
"""

import socket
import traceback
from typing import List, Optional

from dimsdk import ID

from startrek import Docker, DockerStatus
from startrek import Arrival

from ..utils import hex_encode, random_bytes
from ..utils import Log, Logging
from ..common import SessionDBI
from ..conn import BaseSession
from ..conn import WSArrival, MarsStreamArrival, MTPStreamArrival


def generate_session_key() -> str:
    """ generate random string """
    return hex_encode(random_bytes(32))


class ServerSession(BaseSession, Logging):
    """
        Session for Connection
        ~~~~~~~~~~~~~~~~~~~~~~

        'key' - Session Key
                A random string generated when session initialized.
                It's used in handshaking for authentication.

        'ID' - Remote User ID
                It will be set after handshake accepted.
                So we can trust all message from this sender after that.

        'active' - Session Status
                It will be set to True after connection build.
                After receive 'offline' command, it will be set to False;
                and when receive 'online' it will be True again.
                Only push message when it's True.
    """

    def __init__(self, remote: tuple, sock: socket.socket, database: SessionDBI):
        super().__init__(remote=remote, sock=sock, database=database)
        self.__key = generate_session_key()

    @property
    def key(self) -> str:
        return self.__key

    @property  # Override
    def identifier(self) -> Optional[ID]:
        return super().identifier

    @identifier.setter  # Override
    def identifier(self, user: ID):
        old = super().identifier
        if user == old:
            return
        # noinspection PyUnresolvedReferences
        super(ServerSession, ServerSession).identifier.__set__(self, user)
        load_cached_messages(session=self)

    @property  # Override
    def active(self) -> bool:
        return super().active

    @active.setter  # Override
    def active(self, flag: bool):
        old = super().active
        if flag == old:
            return
        # noinspection PyUnresolvedReferences
        super(ServerSession, ServerSession).active.__set__(self, flag)
        load_cached_messages(session=self)

    @property  # Override
    def running(self) -> bool:
        if super().running:
            gate = self.gate
            conn = gate.get_connection(remote=self.remote_address, local=None)
            return not (conn is None or conn.closed)

    #
    #   Docker Delegate
    #

    # Override
    def docker_status_changed(self, previous: DockerStatus, current: DockerStatus, docker: Docker):
        # super().docker_status_changed(previous=previous, current=current, docker=docker)
        if current is None or current == DockerStatus.ERROR:
            # connection error or session finished
            self.active = False
            self.stop()
            # TODO: post notification - DISCONNECTED
            # NotificationCenter().post(name=NotificationNames.DISCONNECTED, sender=self, info={
            #     'session': self,
            # })
        elif current == DockerStatus.READY:
            # connected/reconnected
            self.active = True
            # TODO: post notification - CONNECTED
            # NotificationCenter().post(name=NotificationNames.CONNECTED, sender=self, info={
            #     'session': self,
            # })

    # Override
    def docker_received(self, ship: Arrival, docker: Docker):
        # super().docker_received(ship=ship, docker=docker)
        all_responses = []
        messenger = self.messenger
        packages = get_data_packages(ship=ship)
        for pack in packages:
            try:
                responses = messenger.process_package(data=pack)
                for res in responses:
                    if res is None or len(res) == 0:
                        # should not happen
                        continue
                    all_responses.append(res)
            except Exception as error:
                source = docker.remote_address
                self.error('parse message failed (%s): %s, %s' % (source, error, pack))
                traceback.print_exc()
                # from dimsdk import TextContent
                # return TextContent.new(text='parse message failed: %s' % error)
        gate = self.gate
        source = docker.remote_address
        destination = docker.local_address
        if len(all_responses) > 0:
            # respond separately
            for res in all_responses:
                gate.send_response(payload=res, ship=ship, remote=source, local=destination)
        elif isinstance(ship, MarsStreamArrival):
            # station MUST respond something to client request (Tencent Mars)
            gate.send_response(payload=b'', ship=ship, remote=source, local=destination)


def get_data_packages(ship: Arrival) -> List[bytes]:
    # get payload
    if isinstance(ship, MTPStreamArrival):
        payload = ship.payload
    elif isinstance(ship, MarsStreamArrival):
        payload = ship.payload
    elif isinstance(ship, WSArrival):
        payload = ship.payload
    else:
        raise ValueError('unknown arrival ship: %s' % ship)
    # check payload
    if payload is None or len(payload) == 0:
        return []
    elif payload.startswith(b'{'):
        # JsON in lines
        return payload.splitlines()
    else:
        # TODO: other format?
        return [payload]


def load_cached_messages(session: ServerSession) -> int:
    identifier = session.identifier
    if identifier is None or not session.active:
        return -1
    messenger = session.messenger
    db = messenger.database
    messages = db.reliable_messages(receiver=identifier)
    cnt = len(messages)
    Log.info(msg='[DB] %d cached message(s) loaded for: %s' % (cnt, identifier))
    for msg in messages:
        data = messenger.serialize_message(msg=msg)
        session.queue_message_package(msg=msg, data=data, priority=1)
    return cnt
