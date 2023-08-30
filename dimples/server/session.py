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
from typing import Optional, List, Tuple

from dimsdk import ID

from startrek import Docker, DockerStatus
from startrek import Arrival

from ..utils import hex_encode, random_bytes
from ..utils import Log
from ..common import SessionDBI
from ..common import ReliableMessageDBI
from ..conn import BaseSession
from ..conn import WSArrival, MarsStreamArrival, MTPStreamArrival

from .push import PushCenter


def generate_session_key() -> str:
    """ generate random string """
    return hex_encode(random_bytes(32))


class ServerSession(BaseSession):
    """
        Session for Connection
        ~~~~~~~~~~~~~~~~~~~~~~

        'key' - Session Key
                A random string generated when session initialized.
                It's used in handshaking for authentication.

        'ID' - Remote User ID
                It will be set after handshake accepted.
                So we can trust all messages from this sender after that.

        'active' - Session Status
                It will be set to True after connection build.
                After received 'offline' command, it will be set to False;
                and when received 'online' it will be True again.
                Only push message when it's True.
    """

    def __init__(self, remote: Tuple[str, int], sock: socket.socket, database: SessionDBI):
        super().__init__(remote=remote, sock=sock, database=database)
        self.__key = generate_session_key()

    @property
    def key(self) -> str:
        return self.__key

    async def __load_cached_messages(self):
        if self.identifier is None or not self.active:
            return False
        # load cached message asynchronously
        await load_cached_messages(self)
        return True

    # Override
    def set_identifier(self, identifier: ID) -> bool:
        old = self.identifier
        if super().set_identifier(identifier=identifier):
            session_change_id(session=self, new_id=identifier, old_id=old)
            self.__load_cached_messages()
            return True

    # Override
    def set_active(self, active: bool, when: float = None) -> bool:
        if super().set_active(active=active, when=when):
            session_change_active(session=self, active=active)
            if active:
                self.__load_cached_messages()
            return True

    @property  # Override
    def running(self) -> bool:
        if super().running:
            gate = self.gate
            conn = gate.get_channel(remote=self.remote_address, local=None)
            return not (conn is None or conn.closed)

    #
    #   Docker Delegate
    #

    # Override
    def docker_status_changed(self, previous: DockerStatus, current: DockerStatus, docker: Docker):
        # super().docker_status_changed(previous=previous, current=current, docker=docker)
        if current is None or current == DockerStatus.ERROR:
            # connection error or session finished
            self.set_active(active=False)
            self.stop()
        elif current == DockerStatus.READY:
            # connected/reconnected
            self.set_active(active=True)

    # Override
    def docker_received(self, ship: Arrival, docker: Docker):
        # super().docker_received(ship=ship, docker=docker)
        all_responses = []
        messenger = self.messenger
        # 1. get data packages from arrival ship's payload
        packages = get_data_packages(ship=ship)
        for pack in packages:
            try:
                # 2. process each data package
                responses = messenger.process_package(data=pack)
                for res in responses:
                    if len(res) == 0:
                        # should not happen
                        continue
                    all_responses.append(res)
            except Exception as error:
                source = docker.remote_address
                self.error(msg='parse message failed (%s): %s, %s' % (source, error, pack))
                traceback.print_exc()
                # from dimsdk import TextContent
                # return TextContent.new(text='parse message failed: %s' % error)
        gate = self.gate
        source = docker.remote_address
        destination = docker.local_address
        # 3. send responses
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


# noinspection PyUnusedLocal
def session_change_id(session: ServerSession, new_id: ID, old_id: Optional[ID]):
    if new_id is not None:  # and session.active:
        # user online, clear badges
        center = PushCenter()
        center.reset_badge(identifier=new_id)


def session_change_active(session: ServerSession, active: bool):
    identifier = session.identifier
    if identifier is None:
        # user not login yet
        return False
    elif active:
        # user online, clear badges
        center = PushCenter()
        center.reset_badge(identifier=identifier)
        return True


async def load_cached_messages(session: ServerSession):
    identifier = session.identifier
    assert identifier is not None and session.active, 'session error: %s' % identifier
    messenger = session.messenger
    db = messenger.database
    limit = ReliableMessageDBI.CACHE_LIMIT
    messages = db.reliable_messages(receiver=identifier, limit=limit)
    cnt = len(messages)
    Log.info(msg='[DB] %d cached message(s) loaded for: %s' % (cnt, identifier))
    for msg in messages:
        data = messenger.serialize_message(msg=msg)
        session.queue_message_package(msg=msg, data=data, priority=1)
