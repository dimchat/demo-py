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

import weakref
from abc import ABC, abstractmethod
from typing import Optional, List, Set

from dimsdk import ContentType
from dimsdk import EntityType, ID
from dimsdk import ReliableMessage

from ..utils import Logging
from ..common import CommonPacker
from ..common import CommonFacebook
from ..common import MessageDBI, SessionDBI
from ..common import HandshakeCommand, LoginCommand
from ..conn.session import get_sig

from ..client import ClientSession
from ..client import ClientMessenger
from ..client import ClientProcessor

from .config import GlobalVariable
from .config import SharedFacebook


class OctopusMessenger(ClientMessenger, ABC):
    """ Messenger for processing message from remote station """

    def __init__(self, session: ClientSession, facebook: CommonFacebook, database: MessageDBI):
        super().__init__(session=session, facebook=facebook, database=database)
        self.__accepted = False
        self.__octopus: Optional[weakref.ReferenceType] = None
        self.__local_station: Optional[ID] = None

    @property
    def accepted(self) -> bool:
        return self.__accepted

    @property
    def octopus(self):
        client = self.__octopus()
        assert isinstance(client, Octopus), 'octopus error: %s' % client
        return client

    @octopus.setter
    def octopus(self, client):
        self.__octopus = weakref.ref(client)

    @property
    def local_station(self) -> ID:
        return self.__local_station

    @local_station.setter
    def local_station(self, station: ID):
        self.__local_station = station

    @property
    def remote_station(self) -> ID:
        session = self.session
        station = session.station
        return station.identifier

    # Override
    def handshake_success(self):
        self.__accepted = True
        self.info(msg='start bridge for: %s' % self.remote_station)
        super().handshake_success()

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
                       % (msg.type, msg.sender, msg.receiver, self.remote_station, msg.get('traces')))
            return []
        # handshake accepted, redirecting message
        self.info(msg='redirect msg(type=%d): %s -> %s | from %s, traces: %s'
                  % (msg.type, msg.sender, msg.receiver, self.remote_station, msg.get('traces')))
        return self.deliver_message(msg=msg)

    @abstractmethod
    def deliver_message(self, msg: ReliableMessage) -> List[ReliableMessage]:
        """ call octopus to redirect message """
        pass


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


def create_messenger(remote: tuple, clazz, octopus) -> OctopusMessenger:
    # 1. create session with SessionDB
    shared = GlobalVariable()
    session = ClientSession(remote=remote, database=shared.sdb)
    # 2. create messenger with session and MessageDB
    facebook = SharedFacebook()
    messenger = clazz(session=session, facebook=facebook, database=shared.mdb)
    messenger.octopus = octopus
    # 3. create packer, processor, filter for messenger
    #    they have weak references to session, facebook & messenger
    messenger.packer = CommonPacker(facebook=facebook, messenger=messenger)
    messenger.processor = ClientProcessor(facebook=facebook, messenger=messenger)
    # 4. set weak reference messenger in session
    session.messenger = messenger
    messenger.start()
    return messenger


class Octopus(Logging):

    def __init__(self, local_station: ID, local_host: str = '127.0.0.1', local_port: int = 9394):
        super().__init__()
        self.__local_station = local_station
        self.__inner_messenger = create_messenger(remote=(local_host, local_port), clazz=InnerMessenger, octopus=self)
        self.__outer_messengers: Set[OctopusMessenger] = set()
        self.__outer_messenger_map = weakref.WeakValueDictionary()
        self.__database: Optional[SessionDBI] = None

    @property
    def database(self) -> SessionDBI:
        return self.__database

    @database.setter
    def database(self, db: SessionDBI):
        self.__database = db

    @property
    def local_station(self) -> ID:
        return self.__local_station

    @property
    def inner_messenger(self) -> OctopusMessenger:
        return self.__inner_messenger

    def add_outer_messenger(self, identifier: ID, host: str, port: int):
        messenger = create_messenger(remote=(host, port), clazz=OuterMessenger, octopus=self)
        self.__outer_messengers.add(messenger)
        self.__outer_messenger_map[identifier] = messenger

    def get_outer_messenger(self, identifier: ID):
        return self.__outer_messenger_map[identifier]

    def stop_all(self):
        inner = self.inner_messenger
        inner.stop()
        outers = set(self.__outer_messengers)
        for out in outers:
            out.stop()

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
        roaming = get_roaming_station(receiver=receiver, database=self.database)
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


def get_roaming_station(receiver: ID, database: SessionDBI) -> Optional[ID]:
    """ get login command for roaming station """
    cmd, msg = database.login_command_message(identifier=receiver)
    if isinstance(cmd, LoginCommand):
        station = cmd.station
        assert isinstance(station, dict), 'login command error: %s' % cmd
        return ID.parse(identifier=station.get('ID'))
