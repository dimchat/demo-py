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

    Edges for neighbour stations
"""

import threading
import time
import weakref
from abc import ABC, abstractmethod
from typing import Optional, List, Set

from dimsdk import ContentType
from dimsdk import EntityType, ID
from dimsdk import Station
from dimsdk import ReliableMessage

from ..utils import Logging
from ..utils import Runner
from ..common import CommonPacker
from ..common import CommonFacebook
from ..common import MessageDBI
from ..common import HandshakeCommand
from ..conn.session import get_sig

from ..client import ClientSession
from ..client import ClientMessenger
from ..client import ClientProcessor
from ..client import Terminal

from .config import GlobalVariable
from .config import SharedFacebook


class OctopusMessenger(ClientMessenger, ABC):
    """ Messenger for processing message from remote station """

    def __init__(self, session: ClientSession, facebook: CommonFacebook, database: MessageDBI):
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
    def octopus(self):
        bot = self.__octopus()
        assert isinstance(bot, Octopus), 'octopus error: %s' % bot
        return bot

    @octopus.setter
    def octopus(self, bot):
        self.__octopus = weakref.ref(bot)

    @property
    def local_station(self) -> ID:
        facebook = self.facebook
        current = facebook.current_user
        return current.identifier

    def __is_handshaking(self, msg: ReliableMessage) -> bool:
        """ check HandshakeCommand sent to this station """
        receiver = msg.receiver
        if receiver.type != EntityType.STATION or receiver != self.local_station:
            # not for this station
            return False
        if msg.type != ContentType.COMMAND:
            # not a command
            return False
        i_msg = self.decrypt_message(msg=msg)
        if i_msg is not None:
            return isinstance(i_msg.content, HandshakeCommand)

    # Override
    def process_reliable_message(self, msg: ReliableMessage) -> List[ReliableMessage]:
        # check for HandshakeCommand
        if self.__is_handshaking(msg=msg):
            self.info(msg='receive handshaking: %s' % msg.sender)
            return super().process_reliable_message(msg=msg)
        # check for cycled message
        if msg.receiver == msg.sender:
            self.error(msg='drop cycled msg(type=%d): %s -> %s | from %s, traces: %s'
                       % (msg.type, msg.sender, msg.receiver, get_remote_station(messenger=self), msg.get('traces')))
            return []
        # handshake accepted, redirecting message
        self.info(msg='redirect msg(type=%d): %s -> %s | from %s, traces: %s'
                  % (msg.type, msg.sender, msg.receiver, get_remote_station(messenger=self), msg.get('traces')))
        return self.deliver_message(msg=msg)

    @abstractmethod
    def deliver_message(self, msg: ReliableMessage) -> List[ReliableMessage]:
        """ call octopus to redirect message """
        pass


def get_remote_station(messenger: ClientMessenger) -> ID:
    session = messenger.session
    station = session.station
    return station.identifier


class InnerMessenger(OctopusMessenger):
    """ Messenger for local station """

    # Override
    def deliver_message(self, msg: ReliableMessage) -> List[ReliableMessage]:
        octopus = self.octopus
        return octopus.outgo_message(msg=msg)


class OuterMessenger(OctopusMessenger):
    """ Messenger for remote station """

    # Override
    def deliver_message(self, msg: ReliableMessage) -> List[ReliableMessage]:
        octopus = self.octopus
        return octopus.income_message(msg=msg)

    # Override
    def handshake_success(self):
        super().handshake_success()
        station = self.session.station
        octopus = self.octopus
        octopus.add_index(identifier=station.identifier, terminal=self.terminal)


def create_messenger(user: ID, host: str, port: int, octopus, clazz) -> OctopusMessenger:
    shared = GlobalVariable()
    facebook = SharedFacebook()
    # 0. create station with remote host & port
    station = Station(host=host, port=port)
    station.data_source = facebook
    # 1. create session with SessionDB
    session = ClientSession(station=station, database=shared.sdb)
    session.identifier = user
    # 2. create messenger with session and MessageDB
    messenger = clazz(session=session, facebook=facebook, database=shared.mdb)
    assert isinstance(messenger, OctopusMessenger)
    # 3. create packer, processor for messenger
    #    they have weak references to facebook & messenger
    messenger.packer = CommonPacker(facebook=facebook, messenger=messenger)
    messenger.processor = ClientProcessor(facebook=facebook, messenger=messenger)
    messenger.octopus = octopus
    # 4. set weak reference to messenger
    session.messenger = messenger
    return messenger


def create_terminal(messenger: ClientMessenger) -> Terminal:
    terminal = Terminal(messenger=messenger)
    messenger.terminal = terminal
    terminal.start()
    return terminal


def create_inner_terminal(user: ID, host: str, port: int, octopus) -> Terminal:
    messenger = create_messenger(user=user, host=host, port=port, octopus=octopus, clazz=InnerMessenger)
    return create_terminal(messenger=messenger)


def create_outer_terminal(octopus, user: ID, host: str, port: int) -> Terminal:
    messenger = create_messenger(user=user, host=host, port=port, octopus=octopus, clazz=OuterMessenger)
    return create_terminal(messenger=messenger)


class Octopus(Runner, Logging):

    def __init__(self, local_user: ID, local_host: str = '127.0.0.1', local_port: int = 9394):
        super().__init__()
        self.__user = local_user
        self.__inner = create_inner_terminal(user=local_user, host=local_host, port=local_port, octopus=self)
        self.__outers: Set[Terminal] = set()
        self.__outer_map = weakref.WeakValueDictionary()
        self.__outer_lock = threading.Lock()

    @property
    def inner_messenger(self) -> ClientMessenger:
        terminal = self.__inner
        return terminal.messenger

    def get_outer_messenger(self, identifier: ID) -> Optional[ClientMessenger]:
        with self.__outer_lock:
            terminal = self.__outer_map.get(identifier)
        if terminal is not None:
            return terminal.messenger

    def add_index(self, identifier: ID, terminal: Terminal):
        with self.__outer_lock:
            # self.__outers.add(terminal)
            self.__outer_map[identifier] = terminal

    def connect(self, host: str, port: int = 9394):
        user = self.__user
        terminal = create_outer_terminal(octopus=self, user=user, host=host, port=port)
        with self.__outer_lock:
            self.__outers.add(terminal)

    def start(self):
        thread = threading.Thread(target=self.run)
        thread.start()

    # Override
    def stop(self):
        super().stop()
        inner = self.__inner
        inner.stop()
        with self.__outer_lock:
            outers = set(self.__outers)
        for out in outers:
            out.stop()

    # Override
    def _idle(self):
        time.sleep(60)

    # Override
    def process(self) -> bool:
        with self.__outer_lock:
            outers = set(self.__outers)
        for out in outers:
            if out.is_alive:
                continue
            # remove dead terminal
            sid = out.session.station.identifier
            with self.__outer_lock:
                self.__outers.discard(out)
                if sid is not None:
                    self.__outer_map.pop(sid, None)
        return False

    def income_message(self, msg: ReliableMessage) -> List[ReliableMessage]:
        """ redirect message from remote station """
        receiver = msg.receiver
        messenger = self.inner_messenger
        if messenger.send_reliable_message(msg=msg):
            sig = get_sig(msg=msg)
            self.info(msg='redirected msg (%s) for roaming receiver (%s)' % (sig, receiver))
            # no need to respond receipt for station
            return []
        sig = get_sig(msg=msg)
        self.error(msg='failed to redirect msg (%s) for roaming receiver (%s)' % (sig, receiver))
        return []

    def outgo_message(self, msg: ReliableMessage) -> List[ReliableMessage]:
        """ redirect message to remote station """
        receiver = msg.receiver
        roaming = ID.parse(identifier=msg.get('roaming'))
        if roaming is None:
            # roaming station not found
            self.info(msg='cannot get roaming station for receiver (%s)' % receiver)
            return []
        messenger = self.get_outer_messenger(identifier=roaming)
        if messenger is None:
            # roaming station not my neighbour
            self.info(msg='receiver (%s) is roaming to (%s), but not my neighbour' % (receiver, roaming))
            return []
        if messenger.send_reliable_message(msg=msg):
            sig = get_sig(msg=msg)
            self.info(msg='redirected msg (%s) to (%s) for roaming receiver (%s)' % (sig, roaming, receiver))
            # no need to respond receipt for station
            return []
        sig = get_sig(msg=msg)
        self.error(msg='failed to redirect msg (%s) to (%s) for roaming receiver (%s)' % (sig, roaming, receiver))
        return []
