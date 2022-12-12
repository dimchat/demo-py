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
import time
import weakref
from abc import ABC, abstractmethod
from typing import Optional, List, Set

from dimsdk import ContentType
from dimsdk import EntityType, ID
from dimsdk import ReliableMessage

from ..utils import Logging
from ..utils import Runner
from ..common import CommonPacker
from ..common import CommonFacebook
from ..common import MessageDBI, SessionDBI
from ..common import HandshakeCommand
from ..conn.session import get_sig

from ..client import ClientSession
from ..client import ClientMessenger
from ..client import ClientProcessor
from ..client import Terminal

from .shared import GlobalVariable
from .shared import create_session


class Octopus(Runner, Logging):

    def __init__(self, shared: GlobalVariable, local_host: str = '127.0.0.1', local_port: int = 9394):
        super().__init__()
        self.__shared = shared
        self.__inner = self.create_inner_terminal(host=local_host, port=local_port)
        self.__outers: Set[Terminal] = set()
        self.__outer_map = weakref.WeakValueDictionary()
        self.__outer_lock = threading.Lock()

    @property
    def shared(self) -> GlobalVariable:
        return self.__shared

    @property
    def database(self) -> SessionDBI:
        return self.__shared.sdb

    @property
    def inner_messenger(self) -> ClientMessenger:
        terminal = self.__inner
        return terminal.messenger

    def get_outer_messenger(self, identifier: ID) -> Optional[ClientMessenger]:
        with self.__outer_lock:
            terminal = self.__outer_map.get(identifier)
        if terminal is not None:
            return terminal.messenger

    def create_inner_terminal(self, host: str, port: int) -> Terminal:
        messenger = create_messenger(host=host, port=port, octopus=self, clazz=InnerMessenger)
        return create_terminal(messenger=messenger)

    def create_outer_terminal(self, host: str, port: int) -> Terminal:
        messenger = create_messenger(host=host, port=port, octopus=self, clazz=OuterMessenger)
        return create_terminal(messenger=messenger)

    def add_index(self, identifier: ID, terminal: Terminal):
        with self.__outer_lock:
            # self.__outers.add(terminal)
            self.__outer_map[identifier] = terminal

    def connect(self, host: str, port: int = 9394):
        terminal = self.create_outer_terminal(host=host, port=port)
        with self.__outer_lock:
            self.__outers.add(terminal)

    def start(self):
        thread = threading.Thread(target=self.run)
        thread.start()

    # Override
    def stop(self):
        super().stop()
        inner = self.__inner
        if inner is not None:
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
        # get all neighbor stations
        db = self.database
        neighbors = db.all_neighbors()
        # get all outer terminals
        with self.__outer_lock:
            outers = set(self.__outers)
        for out in outers:
            # check station
            station = out.session.station
            host = station.host
            port = station.port
            for item in neighbors:
                if item[0] == host and item[1] == port:
                    # got
                    neighbors.discard(item)
                    break
            if out.is_alive:
                # outer terminal alive, ignore it
                continue
            # remove dead terminal
            sid = station.identifier
            with self.__outer_lock:
                self.__outers.discard(out)
                if sid is not None:
                    self.__outer_map.pop(sid, None)
        # check new neighbors
        for item in neighbors:
            host = item[0]
            port = item[1]
            sid = item[2]
            self.info(msg='connecting neighbor station "%s" (%s:%d)' % (sid, host, port))
            self.connect(host=host, port=port)
        return False

    def income_message(self, msg: ReliableMessage, priority: int = 0) -> List[ReliableMessage]:
        """ redirect message from remote station """
        messenger = self.inner_messenger
        if messenger.send_reliable_message(msg=msg, priority=priority):
            sig = get_sig(msg=msg)
            self.info(msg='redirected msg (%s) for receiver (%s)' % (sig, msg.receiver))
            # no need to respond receipt for station
            return []
        sig = get_sig(msg=msg)
        self.error(msg='failed to redirect msg (%s) for receiver (%s)' % (sig, msg.receiver))
        return []

    def outgo_message(self, msg: ReliableMessage, priority: int = 0) -> List[ReliableMessage]:
        """ redirect message to remote station """
        target = ID.parse(identifier=msg.get('neighbor'))
        if target is None:
            # target station not found
            self.info(msg='cannot get target station for receiver (%s)' % msg.receiver)
            return []
        messenger = self.get_outer_messenger(identifier=target)
        if messenger is None:
            # target station not my neighbor
            self.info(msg='receiver (%s) is targeted to (%s), but not my neighbor' % (msg.receiver, target))
            return []
        msg.pop('neighbor', None)
        if messenger.send_reliable_message(msg=msg, priority=priority):
            sig = get_sig(msg=msg)
            self.info(msg='redirected msg (%s) to target (%s) for receiver (%s)' % (sig, target, msg.receiver))
            # no need to respond receipt for station
            return []
        sig = get_sig(msg=msg)
        self.error(msg='failed to redirect msg (%s) to target (%s) for receiver (%s)' % (sig, target, msg.receiver))
        return []


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
        priority = 0  # NORMAL
        if msg.receiver.is_broadcast:
            priority = 1  # SLOWER
        octopus = self.octopus
        return octopus.outgo_message(msg=msg, priority=priority)


class OuterMessenger(OctopusMessenger):
    """ Messenger for remote station """

    # Override
    def process_reliable_message(self, msg: ReliableMessage) -> List[ReliableMessage]:
        if msg.sender == self.local_station:
            self.debug(msg='cycled message from this station: %s => %s' % (msg.sender, msg.receiver))
            return []
        return super().process_reliable_message(msg=msg)

    # Override
    def deliver_message(self, msg: ReliableMessage) -> List[ReliableMessage]:
        priority = 0  # NORMAL
        if msg.receiver.is_broadcast:
            priority = 1  # SLOWER
        octopus = self.octopus
        return octopus.income_message(msg=msg, priority=priority)

    # Override
    def handshake_success(self):
        super().handshake_success()
        station = self.session.station
        octopus = self.octopus
        octopus.add_index(identifier=station.identifier, terminal=self.terminal)


def create_messenger(host: str, port: int, octopus: Octopus, clazz) -> OctopusMessenger:
    assert issubclass(clazz, OctopusMessenger), 'messenger class error: %s' % clazz
    shared = octopus.shared
    facebook = shared.facebook
    # 1. create station with remote host & port
    session = create_session(facebook=facebook, database=shared.sdb, host=host, port=port)
    # 2. create messenger with session and MessageDB
    messenger = clazz(session=session, facebook=facebook, database=shared.mdb)
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
