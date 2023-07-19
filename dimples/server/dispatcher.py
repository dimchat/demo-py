# -*- coding: utf-8 -*-
# ==============================================================================
# MIT License
#
# Copyright (c) 2022 Albert Moky
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
    Message Dispatcher
    ~~~~~~~~~~~~~~~~~~

    A dispatcher to decide which way to deliver message.
"""

import threading
from abc import ABC, abstractmethod
from typing import Optional, List

from dimsdk import EntityType, ID
from dimsdk import Content, ReceiptCommand
from dimsdk import ReliableMessage

from ..utils import Singleton, Logging, Runner
from ..common import CommonFacebook
from ..common import MessageDBI, SessionDBI
from ..common import ReliableMessageDBI
from ..common import LoginCommand

from .session_center import SessionCenter
from .push import PushCenter


class MessageDeliver(ABC):
    """ Delegate for deliver message """

    @abstractmethod
    def deliver_message(self, msg: ReliableMessage, receiver: ID) -> List[Content]:
        """
        Deliver message to destination

        :param msg:      message delivering
        :param receiver: message destination
        :return: responses
        """
        raise NotImplemented


@Singleton
class Dispatcher(MessageDeliver):

    def __init__(self):
        super().__init__()
        self.__facebook: Optional[CommonFacebook] = None
        self.__mdb: Optional[MessageDBI] = None
        self.__sdb: Optional[SessionDBI] = None
        # actually deliver worker
        self.__worker: Optional[DeliverWorker] = None
        # roaming user receptionist
        self.__roamer: Optional[Roamer] = None

    @property
    def facebook(self) -> CommonFacebook:
        return self.__facebook

    @facebook.setter
    def facebook(self, barrack: CommonFacebook):
        self.__facebook = barrack

    #
    #   Database
    #

    @property
    def mdb(self) -> MessageDBI:
        return self.__mdb

    @mdb.setter
    def mdb(self, db: MessageDBI):
        self.__mdb = db

    @property
    def sdb(self) -> SessionDBI:
        return self.__sdb

    @sdb.setter
    def sdb(self, db: SessionDBI):
        self.__sdb = db

    #
    #   Worker
    #

    @property
    def deliver_worker(self):  # -> DeliverWorker:
        worker = self.__worker
        if worker is None:
            db = self.sdb
            facebook = self.facebook
            assert db is not None and facebook is not None, 'dispatcher not initialized'
            worker = DeliverWorker(database=db, facebook=facebook)
            self.__worker = worker
        return worker

    #
    #   Roamer
    #

    @property
    def roamer(self):  # -> Roamer
        runner = self.__roamer
        if runner is None:
            db = self.mdb
            assert db is not None, 'dispatcher not initialized'
            runner = Roamer(database=db)
            self.__roamer = runner
            runner.start()
        return runner

    def add_roaming(self, user: ID, station: ID) -> bool:
        """ Add roaming user with station """
        roamer = self.roamer
        return roamer.add_roaming(user=user, station=station)

    #
    #   Deliver
    #

    # Override
    def deliver_message(self, msg: ReliableMessage, receiver: ID) -> List[Content]:
        """ Deliver message to destination """
        worker = self.deliver_worker
        if receiver.type == EntityType.STATION:
            # message to other stations
            # station won't roam to other station, so just push for it directly
            responses = worker.redirect_message(msg=msg, neighbor=receiver)
        elif receiver.type == EntityType.BOT:
            # message to a bot
            # save message before trying to push
            self.__save_reliable_message(msg=msg, receiver=receiver)
            responses = worker.push_message(msg=msg, receiver=receiver)
        else:
            # message to user
            # save message before trying to push
            self.__save_reliable_message(msg=msg, receiver=receiver)
            responses = worker.push_message(msg=msg, receiver=receiver)
            if responses is None:
                # failed to push message, user not online and not roamed to other station,
                # push notification for the receiver
                center = PushCenter()
                center.push_notification(msg=msg)
        # OK
        if responses is None:
            # user not online, and not roaming to other station
            text = 'Message cached.'
            res = ReceiptCommand.create(text=text, msg=msg)
            return [res]
        elif len(responses) == 0:
            # user roamed to other station, but bridge not found
            text = 'Message received.'
            res = ReceiptCommand.create(text=text, msg=msg)
            return [res]
        else:
            # message delivered
            return responses

    def __save_reliable_message(self, msg: ReliableMessage, receiver: ID) -> bool:
        if receiver.type == EntityType.STATION or msg.sender.type == EntityType.STATION:
            # no need to save station message
            return False
        db = self.__mdb
        return db.cache_reliable_message(msg=msg, receiver=receiver)


class RoamingInfo:

    def __init__(self, user: ID, station: ID):
        super().__init__()
        self.user = user
        self.station = station


class Roamer(Runner, Logging):
    """ Delegate for redirect cached messages to roamed station """

    def __init__(self, database: MessageDBI):
        super().__init__()
        self.__database = database
        # roaming (user id => station id)
        self.__queue: List[RoamingInfo] = []
        self.__lock = threading.Lock()

    @property
    def database(self) -> Optional[MessageDBI]:
        return self.__database

    def __append(self, info: RoamingInfo):
        with self.__lock:
            self.__queue.append(info)

    def __next(self) -> Optional[RoamingInfo]:
        with self.__lock:
            if len(self.__queue) > 0:
                return self.__queue.pop(0)

    def add_roaming(self, user: ID, station: ID) -> bool:
        """
        Add roaming user with station

        :param user:    roaming user
        :param station: station roamed to
        :return: False on error
        """
        info = RoamingInfo(user=user, station=station)
        self.__append(info=info)
        return True

    # Override
    def process(self) -> bool:
        info = self.__next()
        if info is None:
            # nothing to do
            return False
        receiver = info.user
        roaming = info.station
        limit = ReliableMessageDBI.CACHE_LIMIT
        try:
            db = self.database
            cached_messages = db.reliable_messages(receiver=receiver, limit=limit)
            self.debug(msg='got %d cached messages for roaming user: %s' % (len(cached_messages), receiver))
            # get deliver delegate for receiver
            dispatcher = Dispatcher()
            worker = dispatcher.deliver_worker
            # deliver cached messages one by one
            for msg in cached_messages:
                worker.push_message(msg=msg, receiver=receiver)
        except Exception as e:
            self.error(msg='process roaming user (%s => %s) error: %s' % (receiver, roaming, e))
        # return True to process next immediately
        return True

    def start(self):
        thread = threading.Thread(target=self.run, daemon=True)
        thread.start()


class DeliverWorker(Logging):
    """ Actual deliver worker """

    def __init__(self, database: SessionDBI, facebook: CommonFacebook):
        super().__init__()
        self.__database = database
        self.__facebook = facebook

    @property
    def database(self) -> Optional[SessionDBI]:
        return self.__database

    @property
    def facebook(self) -> Optional[CommonFacebook]:
        return self.__facebook

    def push_message(self, msg: ReliableMessage, receiver: ID) -> Optional[List[Content]]:
        """
        Push message for receiver

        :param msg:      network message
        :param receiver: actual receiver
        :return: responses
        """
        assert receiver.is_user, 'receiver ID error: %s' % receiver
        assert receiver.type != EntityType.STATION, 'should not push message for station: %s' % receiver
        # 1. try to push message directly
        if session_push(msg=msg, receiver=receiver) > 0:
            text = 'Message delivered.'
            cmd = ReceiptCommand.create(text=text, msg=msg)
            cmd['recipient'] = str(receiver)
            return [cmd]
        # 2. get roaming station
        roaming = get_roaming_station(receiver=receiver, database=self.database)
        if roaming is None:
            # login command not found
            # return None to tell the push center to push notification for it.
            return None
        # 3. redirect message to roaming station
        return self.redirect_message(msg=msg, neighbor=roaming)

    def redirect_message(self, msg: ReliableMessage, neighbor: ID) -> Optional[List[Content]]:
        """
        Redirect message to neighbor station

        :param msg:      network message
        :param neighbor: neighbor station
        :return: responses
        """
        """ Redirect message to neighbor station """
        assert neighbor.type == EntityType.STATION, 'neighbor station ID error: %s' % neighbor
        self.info(msg='redirect message %s => %s to neighbor station: %s' % (msg.sender, msg.receiver, neighbor))
        # 0. check current station
        current = self.facebook.current_user.identifier
        assert current.type == EntityType.STATION, 'current station ID error: %s' % current
        if neighbor == current:
            self.debug(msg='same destination: %s, msg %s => %s' % (neighbor, msg.sender, msg.receiver))
            # the user is roaming to current station, but it's not online now
            # return None to tell the push center to push notification for it.
            return None
        # 1. try to push message to neighbor station directly
        if session_push(msg=msg, receiver=neighbor) > 0:
            text = 'Message redirected.'
            cmd = ReceiptCommand.create(text=text, msg=msg)
            cmd['neighbor'] = str(neighbor)
            return [cmd]
        # 2. push message to bridge
        return bridge_message(msg=msg, neighbor=neighbor, bridge=current)


def bridge_message(msg: ReliableMessage, neighbor: ID, bridge: ID) -> Optional[List[Content]]:
    """
    Redirect message to neighbor station via the station bridge

    :param msg:      network message
    :param neighbor: roaming station
    :param bridge:   current station
    :return: responses
    """
    # NOTE: the messenger will serialize this message immediately, so
    #       we don't need to clone this dictionary to avoid 'neighbor'
    #       be changed to another value before pushing to the bridge.
    # clone = msg.copy_dictionary()
    # msg = ReliableMessage.parse(msg=clone)
    msg['neighbor'] = str(neighbor)
    if session_push(msg=msg, receiver=bridge) > 0:
        text = 'Message redirected.'
        cmd = ReceiptCommand.create(text=text, msg=msg)
        cmd['neighbor'] = str(neighbor)
        return [cmd]
    else:
        # station bridge not found
        # return an empty array to avoid calling push center
        return []


def session_push(msg: ReliableMessage, receiver: ID) -> int:
    """ push message via active session(s) of receiver """
    success = 0
    center = SessionCenter()
    active_sessions = center.active_sessions(identifier=receiver)
    for session in active_sessions:
        if session.send_reliable_message(msg=msg):
            success += 1
    return success


def get_roaming_station(receiver: ID, database: SessionDBI) -> Optional[ID]:
    """ get login command for roaming station """
    cmd, msg = database.login_command_message(user=receiver)
    if isinstance(cmd, LoginCommand):
        station = cmd.station
        assert isinstance(station, dict), 'login command error: %s' % cmd
        return ID.parse(identifier=station.get('ID'))
