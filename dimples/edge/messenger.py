# -*- coding: utf-8 -*-
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
    Octopus
    ~~~~~~~

    Edges for neighbor stations
"""

import weakref
from abc import ABC, abstractmethod
from typing import Optional, List

from dimsdk import ContentType
from dimsdk import EntityType, ID
from dimsdk import ReliableMessage
from dimsdk import Station

from ..utils import Log
from ..utils import get_msg_sig
from ..common import ProviderInfo
from ..common import MessageDBI, SessionDBI
from ..common import HandshakeCommand

from ..client import ClientSession
from ..client import ClientFacebook
from ..client import ClientMessenger
from ..client import Terminal

from .octopus import Octopus


class OctopusMessenger(ClientMessenger, ABC):
    """ Messenger for processing message from remote station """

    def __init__(self, session: ClientSession, facebook: ClientFacebook, database: MessageDBI):
        super().__init__(session=session, facebook=facebook, database=database)
        self.__terminal: Optional[weakref.ReferenceType] = None
        self.__octopus: Optional[weakref.ReferenceType] = None

    @property
    def terminal(self) -> Terminal:
        return self.__terminal()

    @terminal.setter
    def terminal(self, client: Terminal):
        self.__terminal = weakref.ref(client)

    @property
    def octopus(self) -> Optional[Octopus]:
        ref = self.__octopus
        bot = None if ref is None else ref()
        assert isinstance(bot, Octopus), 'octopus error: %s' % bot
        return bot

    @octopus.setter
    def octopus(self, bot: Octopus):
        self.__octopus = weakref.ref(bot)

    @property
    async def local_station(self) -> ID:
        facebook = self.facebook
        current = await facebook.current_user
        return current.identifier

    async def __is_handshaking(self, msg: ReliableMessage) -> bool:
        """ check HandshakeCommand sent to this station """
        local_station = await self.local_station
        receiver = msg.receiver
        if receiver.type != EntityType.STATION or receiver != local_station:
            # not for this station
            return False
        if msg.type != ContentType.COMMAND:
            # not a command
            return False
        i_msg = await self.decrypt_message(msg=msg)
        if i_msg is not None:
            return isinstance(i_msg.content, HandshakeCommand)

    # Override
    async def process_reliable_message(self, msg: ReliableMessage) -> List[ReliableMessage]:
        # check for HandshakeCommand
        if await self.__is_handshaking(msg=msg):
            self.info(msg='receive handshaking: %s' % msg.sender)
            return await super().process_reliable_message(msg=msg)
        # check for cycled message
        if msg.receiver == msg.sender:
            self.error(msg='drop cycled msg(type=%s): %s -> %s | from %s, traces: %s'
                       % (msg.type, msg.sender, msg.receiver, get_remote_station(messenger=self), msg.get('traces')))
            return []
        # handshake accepted, redirecting message
        sig = get_msg_sig(msg=msg)
        self.info(msg='redirect msg(type=%s, sig=%s): %s -> %s | from %s, traces: %s'
                  % (msg.type, sig, msg.sender, msg.receiver, get_remote_station(messenger=self), msg.get('traces')))
        return await self._deliver_message(msg=msg)

    @abstractmethod
    async def _deliver_message(self, msg: ReliableMessage) -> List[ReliableMessage]:
        """ call octopus to redirect message """
        return []


def get_remote_station(messenger: ClientMessenger) -> ID:
    session = messenger.session
    station = session.station
    return station.identifier


class InnerMessenger(OctopusMessenger):
    """ Messenger for local station """

    # Override
    async def _deliver_message(self, msg: ReliableMessage) -> List[ReliableMessage]:
        priority = 0  # NORMAL
        if msg.receiver.is_broadcast:
            priority = 1  # SLOWER
        octopus = self.octopus
        return await octopus.outgo_message(msg=msg, priority=priority)


class OuterMessenger(OctopusMessenger):
    """ Messenger for remote station """

    # Override
    async def _deliver_message(self, msg: ReliableMessage) -> List[ReliableMessage]:
        priority = 0  # NORMAL
        if msg.receiver.is_broadcast:
            priority = 1  # SLOWER
        octopus = self.octopus
        return await octopus.income_message(msg=msg, priority=priority)

    # Override
    async def process_reliable_message(self, msg: ReliableMessage) -> List[ReliableMessage]:
        local_station = await self.local_station
        if msg.sender == local_station:
            self.error(msg='cycled message from this station: %s => %s' % (msg.sender, msg.receiver))
            return []
        return await super().process_reliable_message(msg=msg)

    # Override
    async def handshake_success(self):
        await super().handshake_success()
        station = self.session.station
        await update_station(station=station, database=self.octopus.database)
        octopus = self.octopus
        octopus.add_index(identifier=station.identifier, terminal=self.terminal)


async def update_station(station: Station, database: SessionDBI):
    Log.info(msg='update station: %s' % station)
    # SP ID
    provider = station.provider
    if provider is None:
        provider = ProviderInfo.GSP
    # new info
    sid = station.identifier
    host = station.host
    port = station.port
    assert not sid.is_broadcast, 'station ID error: %s' % sid
    assert host is not None and port > 0, 'station error: %s, %d' % (host, port)
    await database.update_station(identifier=sid, host=host, port=port, provider=provider, chosen=0)
