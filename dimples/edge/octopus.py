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

import threading
import weakref
from abc import ABC, abstractmethod
from typing import Optional, List, Set

from dimsdk import ContentType
from dimsdk import EntityType, ID
from dimsdk import ReliableMessage
from dimsdk import Station

from ..utils import Log, Logging
from ..utils import Runner, Daemon
from ..utils import get_msg_sig
from ..common import ProviderInfo
from ..common import MessageDBI, SessionDBI
from ..common import HandshakeCommand

from ..client import ClientSession
from ..client import ClientFacebook
from ..client import ClientMessenger
from ..client import ClientMessagePacker
from ..client import ClientMessageProcessor
from ..client import Terminal

from .shared import GlobalVariable


class InnerClient(Terminal):

    # Override
    def _create_messenger(self, facebook: ClientFacebook, session: ClientSession):
        shared = GlobalVariable()
        messenger = InnerMessenger(session=session, facebook=facebook, database=shared.mdb)
        messenger.terminal = self  # Weak Reference
        shared.messenger = messenger
        return messenger


class OuterClient(Terminal):

    # Override
    def _create_messenger(self, facebook: ClientFacebook, session: ClientSession):
        shared = GlobalVariable()
        archivist = shared.facebook.archivist
        assert archivist is not None, 'archivist not found'
        messenger = OuterMessenger(session=session, facebook=facebook, database=shared.mdb)
        messenger.terminal = self
        archivist.messenger = messenger  # Weak Reference
        return messenger


class Octopus(Runner, Logging):

    def __init__(self, shared: GlobalVariable, local_host: str = '127.0.0.1', local_port: int = 9394):
        super().__init__(interval=60)
        self.__shared = shared
        self.__host = local_host
        self.__port = local_port
        self.__inner: Optional[Terminal] = None
        self.__inner_lock = threading.Lock()
        self.__outers: Set[Terminal] = set()
        self.__outer_map = weakref.WeakValueDictionary()
        self.__outer_lock = threading.Lock()
        self.__daemon = Daemon(target=self)

    @property
    def shared(self) -> GlobalVariable:
        return self.__shared

    @property
    def facebook(self) -> ClientFacebook:
        return self.__shared.facebook

    @property
    def database(self) -> SessionDBI:
        return self.__shared.sdb

    @property
    async def inner_messenger(self) -> ClientMessenger:
        with self.__inner_lock:
            terminal = self.__inner
            if terminal is None:
                terminal = await self.create_inner_terminal(host=self.__host, port=self.__port)
                self.__inner = terminal
        return terminal.messenger

    def get_outer_messenger(self, identifier: ID) -> Optional[ClientMessenger]:
        with self.__outer_lock:
            terminal = self.__outer_map.get(identifier)
        if terminal is not None:
            return terminal.messenger

    async def create_inner_terminal(self, host: str, port: int) -> Terminal:
        terminal = InnerClient(facebook=self.facebook, database=self.database)
        messenger = await terminal.connect(host=host, port=port)
        # set octopus
        assert isinstance(messenger, OctopusMessenger)
        messenger.octopus = self
        # start an async task in background
        await terminal.start()
        return terminal

    async def create_outer_terminal(self, host: str, port: int) -> Terminal:
        terminal = OuterClient(facebook=self.facebook, database=self.database)
        messenger = await terminal.connect(host=host, port=port)
        # set octopus
        assert isinstance(messenger, OctopusMessenger)
        messenger.octopus = self
        # start an async task in background
        await terminal.start()
        return terminal

    def add_index(self, identifier: ID, terminal: Terminal):
        with self.__outer_lock:
            # self.__outers.add(terminal)
            self.__outer_map[identifier] = terminal

    async def connect(self, host: str, port: int = 9394):
        # create a new terminal for remote host:port
        with self.__outer_lock:
            # check exist terminals
            outers = self.__outers.copy()
            for out in outers:
                # check station
                station = out.session.station
                if port == station.port and host == station.host:
                    self.warning(msg='connection already exists: (%s, %d)' % (host, port))
                    # self.__outers.discard(out)
                    return None
            # create new terminal
            terminal = await self.create_outer_terminal(host=host, port=port)
            self.__outers.add(terminal)
            return terminal

    async def start(self):
        if self.running:
            await self.stop()
        # start an async task in background
        self.__daemon.start()

    # Override
    async def stop(self):
        # 1. stop inner terminal
        inner = self.__inner
        if inner is not None:
            await inner.stop()
        # 2. stop outer terminals
        with self.__outer_lock:
            outers = set(self.__outers)
        for out in outers:
            await out.stop()
        # 3. stop runner
        await super().stop()

    # Override
    async def process(self) -> bool:
        # get all neighbor stations
        db = self.database
        providers = await db.all_providers()
        assert len(providers) > 0, 'service provider not found'
        gsp = providers[0].identifier
        neighbors = await db.all_stations(provider=gsp)
        if neighbors is not None:
            neighbors = neighbors.copy()
        # get all outer terminals
        with self.__outer_lock:
            outers = set(self.__outers)
        self.debug(msg='checking %d client(s) with %d neighbor(s)' % (len(outers), len(neighbors)))
        for out in outers:
            # check station
            station = out.session.station
            sid = station.identifier
            host = station.host
            port = station.port
            # reduce neighbors
            for item in neighbors:
                if item.port == port and item.host == host:
                    # got
                    neighbors.remove(item)
                    break
            # check outer client
            if out.running:
                # skip running client
                continue
            else:
                # remove dead client
                self.warning(msg='client stopped, remove it: %s (%s:%d)' % (sid, host, port))
            with self.__outer_lock:
                self.__outers.discard(out)
                if sid is not None:
                    self.__outer_map.pop(sid, None)
        # check new neighbors
        for item in neighbors:
            host = item.host
            port = item.port
            self.debug(msg='connecting neighbor station (%s:%d), client count: %d' % (host, port, len(self.__outers)))
            await self.connect(host=host, port=port)
        return False

    async def income_message(self, msg: ReliableMessage, priority: int = 0) -> List[ReliableMessage]:
        """ redirect message from remote station """
        sender = msg.sender
        receiver = msg.receiver
        sig = get_msg_sig(msg=msg)
        messenger = await self.inner_messenger
        if await messenger.send_reliable_message(msg=msg, priority=priority):
            self.info(msg='redirected msg (%s): %s -> %s' % (sig, sender, receiver))
        else:
            self.error(msg='failed to redirect msg (%s): %s -> %s' % (sig, sender, receiver))
        # no need to respond receipt for station
        return []

    async def outgo_message(self, msg: ReliableMessage, priority: int = 0) -> List[ReliableMessage]:
        """ redirect message to remote station """
        receiver = msg.receiver
        # get neighbor stations
        neighbor = ID.parse(identifier=msg.get('neighbor'))
        if neighbor is not None:
            neighbors = set()
            neighbors.add(neighbor)
            msg.pop('neighbor', None)
        else:
            with self.__outer_lock:
                neighbors = set(self.__outer_map.keys())
        #
        #  0. check recipients
        #
        new_recipients = set()
        old_recipients = msg.get('recipients')
        old_recipients = [] if old_recipients is None else ID.convert(old_recipients)
        for item in neighbors:
            if item in old_recipients:
                self.info(msg='skip exists station: %s' % item)
                continue
            self.info(msg='new neighbor station: %s' % item)
            new_recipients.add(item)
        # update 'recipients' to avoid the new recipients redirect it to same targets
        self.info(msg='append new recipients: %s, %s + %s' % (receiver, new_recipients, old_recipients))
        all_recipients = list(old_recipients) + list(new_recipients)
        msg['recipients'] = ID.revert(all_recipients)
        #
        #  1. send to the new recipients (neighbor stations)
        #
        sig = get_msg_sig(msg=msg)
        failed_neighbors = []
        for target in new_recipients:
            messenger = self.get_outer_messenger(identifier=target)
            if messenger is None:
                # target station not my neighbor
                self.warning(msg='not my neighbor: %s (%s)' % (target, receiver))
                failed_neighbors.append(target)
            elif await messenger.send_reliable_message(msg=msg, priority=priority):
                self.info(msg='redirected msg (%s) to neighbor: %s (%s)' % (sig, target, receiver))
            else:
                self.error(msg='failed to send to neighbor: %s (%s)' % (target, receiver))
                failed_neighbors.append(target)
        if len(failed_neighbors) > 0:
            self.error(msg='failed to redirect msg (%s) for receiver (%s): %s' % (sig, receiver, failed_neighbors))
        return []


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
            self.error(msg='drop cycled msg(type=%d): %s -> %s | from %s, traces: %s'
                       % (msg.type, msg.sender, msg.receiver, get_remote_station(messenger=self), msg.get('traces')))
            return []
        # handshake accepted, redirecting message
        sig = get_msg_sig(msg=msg)
        self.info(msg='redirect msg(type=%d, sig=%s): %s -> %s | from %s, traces: %s'
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


def create_messenger(facebook: ClientFacebook, database: MessageDBI,
                     session: ClientSession, messenger_class) -> OctopusMessenger:
    assert issubclass(messenger_class, OctopusMessenger), 'messenger class error: %s' % messenger_class
    # 1. create messenger with session and MessageDB
    messenger = messenger_class(session=session, facebook=facebook, database=database)
    # 2. create packer, processor for messenger
    #    they have weak references to facebook & messenger
    messenger.packer = ClientMessagePacker(facebook=facebook, messenger=messenger)
    messenger.processor = ClientMessageProcessor(facebook=facebook, messenger=messenger)
    # 3. set weak reference to messenger
    session.messenger = messenger
    return messenger


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
