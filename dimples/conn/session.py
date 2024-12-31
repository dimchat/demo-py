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

from startrek.types import SocketAddress

from dimsdk import ID, Content
from dimsdk import InstantMessage, ReliableMessage

from ..common import CommonMessenger
from ..common import Session, SessionDBI

from .gatekeeper import GateKeeper


class BaseSession(GateKeeper, Session, ABC):

    def __init__(self, remote: SocketAddress, sock: Optional[socket.socket], database: SessionDBI):
        super().__init__(remote=remote, sock=sock)
        self.__database = database
        self.__identifier: Optional[ID] = None
        self.__messenger: Optional[weakref.ReferenceType] = None

    # Override
    def __str__(self) -> str:
        cname = self.__class__.__name__
        return '<%s id="%s" remote="%s" key="%s" />' % (cname, self.identifier, self.remote_address, self.session_key)

    # Override
    def __repr__(self):
        cname = self.__class__.__name__
        return '<%s id="%s" remote="%s" key="%s" />' % (cname, self.identifier, self.remote_address, self.session_key)

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
    def messenger(self) -> Optional[CommonMessenger]:
        ref = self.__messenger
        if ref is not None:
            return ref()

    @messenger.setter
    def messenger(self, transceiver: CommonMessenger):
        self.__messenger = None if transceiver is None else weakref.ref(transceiver)

    # Override
    async def queue_message_package(self, msg: ReliableMessage, data: bytes, priority: int = 0) -> bool:
        ship = await self._porter_pack(payload=data, priority=priority)
        if ship is None:
            self.error(msg='failed to pack msg: %s -> %s, %s' % (msg.sender, msg.receiver, msg.group))
        else:
            return self._queue_append(msg=msg, ship=ship)

    #
    #   Transmitter
    #

    # Override
    async def send_content(self, sender: Optional[ID], receiver: ID, content: Content,
                           priority: int = 0) -> Tuple[InstantMessage, Optional[ReliableMessage]]:
        messenger = self.messenger
        return await messenger.send_content(sender=sender, receiver=receiver, content=content, priority=priority)

    # Override
    async def send_instant_message(self, msg: InstantMessage, priority: int = 0) -> Optional[ReliableMessage]:
        messenger = self.messenger
        return await messenger.send_instant_message(msg=msg, priority=priority)

    # Override
    async def send_reliable_message(self, msg: ReliableMessage, priority: int = 0) -> bool:
        messenger = self.messenger
        return await messenger.send_reliable_message(msg=msg, priority=priority)
