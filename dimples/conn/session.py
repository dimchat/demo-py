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
import weakref
from abc import ABC
from typing import Optional, Tuple

from dimsdk import EntityType, ID, Content
from dimsdk import InstantMessage, ReliableMessage

from startrek import Docker, Departure

from ..common import CommonMessenger
from ..common import Session, SessionDBI
from ..common import MessageDBI

from .gatekeeper import GateKeeper
from .queue import MessageWrapper


class BaseSession(GateKeeper, Session, ABC):

    def __init__(self, remote: Tuple[str, int], sock: Optional[socket.socket], database: SessionDBI):
        super().__init__(remote=remote, sock=sock)
        self.__database = database
        self.__identifier: Optional[ID] = None
        self.__messenger: Optional[weakref.ReferenceType] = None

    @property  # Override
    def database(self) -> SessionDBI:
        return self.__database

    @property  # Override
    def identifier(self) -> Optional[ID]:
        return self.__identifier

    # Override
    def set_identifier(self, identifier: ID) -> bool:
        if self.__identifier != identifier:
            self.__identifier = identifier
            return True

    @property
    def messenger(self) -> CommonMessenger:
        ref = self.__messenger
        assert ref is not None, 'messenger not set yet'
        return ref()

    @messenger.setter
    def messenger(self, transceiver: CommonMessenger):
        self.__messenger = weakref.ref(transceiver)

    # Override
    def queue_message_package(self, msg: ReliableMessage, data: bytes, priority: int = 0) -> bool:
        ship = self._docker_pack(payload=data, priority=priority)
        return self._queue_append(msg=msg, ship=ship)

    #
    #   Transmitter
    #

    # Override
    def send_content(self, sender: Optional[ID], receiver: ID, content: Content,
                     priority: int = 0) -> Tuple[InstantMessage, Optional[ReliableMessage]]:
        messenger = self.messenger
        return messenger.send_content(sender=sender, receiver=receiver, content=content, priority=priority)

    # Override
    def send_instant_message(self, msg: InstantMessage, priority: int = 0) -> Optional[ReliableMessage]:
        messenger = self.messenger
        return messenger.send_instant_message(msg=msg, priority=priority)

    # Override
    def send_reliable_message(self, msg: ReliableMessage, priority: int = 0) -> bool:
        messenger = self.messenger
        return messenger.send_reliable_message(msg=msg, priority=priority)

    #
    #   Docker Delegate
    #

    # Override
    def docker_sent(self, ship: Departure, docker: Docker):
        if isinstance(ship, MessageWrapper):
            msg = ship.msg
            ship.on_sent()
            if isinstance(msg, ReliableMessage):
                # remove from database for actual receiver
                receiver = self.identifier
                db = self.messenger.database
                remove_reliable_message(msg=msg, receiver=receiver, database=db)


def remove_reliable_message(msg: ReliableMessage, receiver: ID, database: MessageDBI):
    # 0. if session ID is empty, means user not login;
    #    this message must be a handshake command, and
    #    its receiver must be the targeted user.
    # 1. if this session is a station, check original receiver;
    #    a message to station won't be stored.
    # 2. if the msg.receiver is a different user ID, means it's
    #    a roaming message, remove it for actual receiver.
    # 3. if the original receiver is a group, it must had been
    #    replaced to the group assistant ID by GroupDeliver.
    if receiver is None or receiver.type == EntityType.STATION:
        # if msg.receiver == receiver:
        #     # station message won't be stored
        #     return False
        receiver = msg.receiver
    sig = get_sig(msg=msg)
    print('[QUEUE] message (%s) sent, remove from db: %s => %s (%s)'
          % (sig, msg.sender, msg.receiver, receiver))
    # remove sent message from database
    return database.remove_reliable_message(msg=msg, receiver=receiver)


def get_sig(msg: ReliableMessage) -> str:
    """ last 6 bytes (signature in base64) """
    sig = msg.get('signature')
    # assert isinstance(sig, str), 'signature error: %s' % sig
    sig = sig.strip()
    return sig[-8:]  # last 6 bytes (signature in base64)
