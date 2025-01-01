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
import threading
import traceback
from typing import Optional, List

from dimsdk import ID, EntityType
from dimsdk import ReliableMessage

from startrek.types import SocketAddress
from startrek import Porter, PorterStatus
from startrek import Arrival, Departure

from ..utils import Log, Runner
from ..utils import hex_encode, random_bytes
from ..utils import get_msg_sig, get_msg_info
from ..common import SessionDBI, MessageDBI, ReliableMessageDBI
from ..conn import MessageWrapper
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

    def __init__(self, remote: SocketAddress, sock: socket.socket, database: SessionDBI):
        super().__init__(remote=remote, sock=sock, database=database)
        self.__key = generate_session_key()
        self.__loader = OfflineMessageLoader()

    @property
    def session_key(self) -> str:
        return self.__key

    @property  # Override
    def running(self) -> bool:
        if super().running:
            status = self.gate.get_porter_status(remote=self.remote_address, local=None)
            return status != PorterStatus.ERROR

    # Override
    def set_identifier(self, identifier: ID) -> bool:
        old = self.identifier
        if super().set_identifier(identifier=identifier):
            session_change_id(session=self, new_id=identifier, old_id=old)
            self.__loader.load_cached_messages(session=self)
            return True

    # Override
    def set_active(self, active: bool, when: float = None) -> bool:
        if super().set_active(active=active, when=when):
            session_change_active(session=self, active=active)
            self.__loader.load_cached_messages(session=self)
            return True

    #
    #   Docker Delegate
    #

    # Override
    async def porter_status_changed(self, previous: PorterStatus, current: PorterStatus, porter: Porter):
        # await super().porter_status_changed(previous=previous, current=current, porter=porter)
        if current is None or current == PorterStatus.ERROR:
            # connection error or session finished
            self.set_active(active=False)
            await porter.close()
            await self.stop()
        elif current == PorterStatus.READY:
            # connected/reconnected
            self.set_active(active=True)

    # Override
    async def porter_received(self, ship: Arrival, porter: Porter):
        # await super().porter_received(ship=ship, porter=porter)
        all_responses = []
        messenger = self.messenger
        # 1. get data packages from arrival ship's payload
        packages = get_data_packages(ship=ship)
        for pack in packages:
            try:
                # 2. process each data package
                responses = await messenger.process_package(data=pack)
                for res in responses:
                    if len(res) == 0:
                        # should not happen
                        continue
                    all_responses.append(res)
            except Exception as error:
                source = porter.remote_address
                self.error(msg='parse message failed (%s): %s, %s' % (source, error, pack))
                traceback.print_exc()
                # from dimsdk import TextContent
                # return TextContent.new(text='parse message failed: %s' % error)
        gate = self.gate
        source = porter.remote_address
        destination = porter.local_address
        # 3. send responses
        if len(all_responses) > 0:
            # respond separately
            for res in all_responses:
                await gate.send_response(payload=res, ship=ship, remote=source, local=destination)
        elif isinstance(ship, MarsStreamArrival):
            # station MUST respond something to client request (Tencent Mars)
            await gate.send_response(payload=b'', ship=ship, remote=source, local=destination)

    # Override
    async def porter_sent(self, ship: Departure, porter: Porter):
        if isinstance(ship, MessageWrapper):
            msg = ship.msg
            if msg is not None:
                # remove from database for actual receiver
                receiver = self.identifier
                db = self.messenger.database
                await remove_reliable_message(msg=msg, receiver=receiver, database=db)


class OfflineMessageLoader:

    def __init__(self):
        super().__init__()
        self.__lock = threading.Lock()
        self.__thread = None

    def load_cached_messages(self, session: ServerSession):
        identifier = session.identifier
        if identifier is None:
            # user not login
            return False
        elif not session.active:
            # session not active
            return False
        thr: threading.Thread = self.__thread
        if thr is not None and thr.is_alive():
            return False
        with self.__lock:
            thr = self.__thread
            if thr is not None and thr.is_alive():
                return False
            # load cached message asynchronously
            coro = _load_cached_messages(identifier=identifier, session=session)
            thr = Runner.async_thread(coro=coro)
            thr.start()
            self.__thread = thr
            return True


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


async def _load_cached_messages(identifier: ID, session: ServerSession):
    messenger = session.messenger
    db = messenger.database
    limit = ReliableMessageDBI.CACHE_LIMIT
    messages = await db.get_reliable_messages(receiver=identifier, limit=limit)
    cnt = len(messages)
    Log.info(msg='[DB] %d cached message(s) loaded for: %s' % (cnt, identifier))
    for msg in messages:
        data = await messenger.serialize_message(msg=msg)
        ok = await session.queue_message_package(msg=msg, data=data, priority=1)
        sig = get_msg_sig(msg=msg)
        Log.info(msg='queue message for: %s, %s, %s' % (identifier, ok, sig))


async def remove_reliable_message(msg: ReliableMessage, receiver: ID, database: MessageDBI):
    # 0. if session ID is empty, means user not login;
    #    this message must be a handshake command, and
    #    its receiver must be the targeted user.
    # 1. if this session is a station, check original receiver;
    #    a message to station won't be stored.
    # 2. if the msg.receiver is a different user ID, means it's
    #    a roaming message, remove it for actual receiver.
    # 3. if the original receiver is a group, it must have been
    #    replaced to the group assistant ID by GroupDeliver.
    if receiver is None or receiver.type == EntityType.STATION:
        # if msg.receiver == receiver:
        #     # station message won't be stored
        #     return False
        receiver = msg.receiver
    info = get_msg_info(msg=msg)
    Log.info(msg='message sent for %s, remove from db: %s' % (receiver, info))
    # remove sent message from database
    return await database.remove_reliable_message(msg=msg, receiver=receiver)
