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
from typing import Optional

from dimsdk import ID, Content
from dimsdk import InstantMessage, ReliableMessage

from startrek import Docker, Departure

from ..common import CommonMessenger
from ..common import Session, SessionDBI

from .gatekeeper import GateKeeper
from .queue import MessageWrapper


class BaseSession(GateKeeper, Session, ABC):

    def __init__(self, remote: tuple, sock: Optional[socket.socket], database: SessionDBI):
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

    @identifier.setter  # Override
    def identifier(self, user: ID):
        self.__identifier = user

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
                     priority: int = 0) -> (InstantMessage, Optional[ReliableMessage]):
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
            if isinstance(msg, ReliableMessage):
                # remove sent message
                sig = msg.get('signature')
                sig = sig[-8:]  # last 6 bytes (signature in base64)
                print('[QUEUE] message sent, remove from db: %s, %s -> %s' % (sig, msg.sender, msg.receiver))
                db = self.messenger.database
                db.remove_reliable_message(msg=msg)
            ship.on_sent()
