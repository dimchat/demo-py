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
from typing import Optional, Set, List

from dimsdk import EntityType, ID, EVERYONE
from dimsdk import Station
from dimsdk import Content, ReceiptCommand
from dimsdk import ReliableMessage

from ..utils import Singleton, Log, Logging, Runner, DaemonRunner
from ..common import CommonFacebook
from ..common import MessageDBI, SessionDBI
from ..common import ReliableMessageDBI
from ..common import LoginCommand

from .session_center import SessionCenter
from .push import PushCenter
from .archivist import ServerArchivist


class MessageDeliver(ABC):
    """ Delegate for deliver message """

    @abstractmethod
    async def deliver_message(self, msg: ReliableMessage, receiver: ID) -> List[Content]:
        """
        Deliver message to destination

        :param msg:      message delivering
        :param receiver: message destination
        :return: responses
        """
        raise NotImplemented


@Singleton
class Dispatcher(MessageDeliver, Logging):

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
            # Runner.async_run(coroutine=runner.start())
            Runner.thread_run(runner)
        return runner

    def add_roaming(self, user: ID, station: ID) -> bool:
        """ Add roaming user with station """
        roamer = self.roamer
        return roamer.add_roaming(user=user, station=station)

    #
    #   Deliver
    #

    # Override
    async def deliver_message(self, msg: ReliableMessage, receiver: ID) -> List[Content]:
        """ Deliver message to destination """
        worker = self.deliver_worker
        if receiver.is_group:
            # broadcast message to neighbor stations
            # e.g.: 'stations@everywhere', 'everyone@everywhere'
            return await self.__deliver_group_message(msg=msg, receiver=receiver)
        elif receiver.type == EntityType.STATION:
            # message to other stations
            # station won't roam to other station, so just push for it directly
            responses = await worker.redirect_message(msg=msg, neighbor=receiver)
        elif receiver.type == EntityType.BOT:
            # message to a bot
            # save message before trying to push
            await self.__save_reliable_message(msg=msg, receiver=receiver)
            responses = await worker.push_message(msg=msg, receiver=receiver)
        else:
            # message to user
            # save message before trying to push
            await self.__save_reliable_message(msg=msg, receiver=receiver)
            responses = await worker.push_message(msg=msg, receiver=receiver)
            if responses is None:
                # failed to push message, user not online and not roamed to other station,
                # push notification for the receiver
                center = PushCenter()
                center.push_notification(msg=msg)
        # OK
        if responses is None:
            # user not online, and not roaming to other station
            text = 'Message cached.'
            res = ReceiptCommand.create(text=text, envelope=msg.envelope)
            return [res]
        elif len(responses) == 0:
            # user roamed to other station, but bridge not found
            text = 'Message received.'
            res = ReceiptCommand.create(text=text, envelope=msg.envelope)
            return [res]
        else:
            # message delivered
            return responses

    async def __deliver_group_message(self, msg: ReliableMessage, receiver: ID) -> List[Content]:
        if receiver == Station.EVERY or receiver == EVERYONE:
            # broadcast message to neighbor stations
            # e.g.: 'stations@everywhere', 'everyone@everywhere'
            archivist = self.facebook.archivist
            assert isinstance(archivist, ServerArchivist)
            candidates = await archivist.all_neighbors
            if len(candidates) == 0:
                self.warning(msg='failed to get neighbors: %s' % receiver)
                return []
            self.info(msg='forward to neighbor stations: %s -> %s' % (receiver, candidates))
            return await self.__broadcast_message(msg=msg, receiver=receiver, neighbors=candidates)
        else:
            self.warning(msg='unknown group: %s' % receiver)
            text = 'Group message not allow for this station'
            res = ReceiptCommand.create(text=text, envelope=msg.envelope)
            return [res]

    async def __broadcast_message(self, msg: ReliableMessage, receiver: ID, neighbors: Set[ID]) -> List[Content]:
        current = self.facebook.current_user
        assert current is not None, 'failed to get current station'
        current = current.identifier
        #
        #  0. check recipients
        #
        new_recipients = set()
        old_recipients = msg.get('recipients')
        old_recipients = [] if old_recipients is None else ID.convert(old_recipients)
        for item in neighbors:
            if item == current:
                self.info(msg='skip current station: %s' % item)
                continue
            elif item in old_recipients:
                self.info(msg='skip exists station: %s' % item)
                continue
            self.info(msg='new neighbor station: %s' % item)
            new_recipients.add(item)
        # set 'recipients' in the msg to avoid the new recipients redirect it to same targets
        self.info(msg='append new recipients: %s, %s + %s' % (receiver, new_recipients, old_recipients))
        all_recipients = list(old_recipients) + list(new_recipients)
        msg['recipients'] = ID.revert(all_recipients)
        #
        #  1. push to neighbor stations directly
        #
        indirect_neighbors = set()
        for target in new_recipients:
            if await session_push(msg=msg, receiver=target) == 0:
                indirect_neighbors.add(target)
        # remove unsuccessful items
        for item in indirect_neighbors:
            new_recipients.discard(item)
        # update 'recipients' before redirect via bridge
        self.info(msg='update recipients: %s, %s + %s' % (receiver, new_recipients, old_recipients))
        all_recipients = list(old_recipients) + list(new_recipients)
        msg['recipients'] = ID.revert(all_recipients)
        #
        #  2. push to other neighbor stations via station bridge
        #
        worker = self.deliver_worker
        await worker.redirect_message(msg=msg, neighbor=None)
        #
        #  OK
        #
        text = 'Message forwarded.'
        cmd = ReceiptCommand.create(text=text, envelope=msg.envelope)
        cmd['recipients'] = ID.revert(new_recipients)
        return [cmd]

    async def __save_reliable_message(self, msg: ReliableMessage, receiver: ID) -> bool:
        if receiver.type == EntityType.STATION or msg.sender.type == EntityType.STATION:
            # no need to save station message
            return False
        elif msg.receiver.is_broadcast:
            # no need to save broadcast message
            return False
        db = self.__mdb
        return await db.cache_reliable_message(msg=msg, receiver=receiver)


class RoamingInfo:

    def __init__(self, user: ID, station: ID):
        super().__init__()
        self.user = user
        self.station = station


class Roamer(DaemonRunner, Logging):
    """ Delegate for redirect cached messages to roamed station """

    def __init__(self, database: MessageDBI):
        super().__init__(interval=Runner.INTERVAL_SLOW)
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
    async def process(self) -> bool:
        info = self.__next()
        if info is None:
            # nothing to do
            return False
        receiver = info.user
        roaming = info.station
        limit = ReliableMessageDBI.CACHE_LIMIT
        try:
            db = self.database
            cached_messages = await db.get_reliable_messages(receiver=receiver, limit=limit)
            self.debug(msg='got %d cached messages for roaming user: %s' % (len(cached_messages), receiver))
            # get deliver delegate for receiver
            dispatcher = Dispatcher()
            worker = dispatcher.deliver_worker
            # deliver cached messages one by one
            for msg in cached_messages:
                await worker.push_message(msg=msg, receiver=receiver)
        except Exception as e:
            self.error(msg='process roaming user (%s => %s) error: %s' % (receiver, roaming, e))
        # return True to process next immediately
        return True


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

    async def push_message(self, msg: ReliableMessage, receiver: ID) -> Optional[List[Content]]:
        """
        Push message for receiver

        :param msg:      network message
        :param receiver: actual receiver
        :return: responses
        """
        assert receiver.is_user, 'receiver ID error: %s' % receiver
        assert receiver.type != EntityType.STATION, 'should not push message for station: %s' % receiver
        # 1. try to push message directly
        if await session_push(msg=msg, receiver=receiver) > 0:
            text = 'Message delivered.'
            cmd = ReceiptCommand.create(text=text, envelope=msg.envelope)
            cmd['recipient'] = str(receiver)
            return [cmd]
        # 2. get roaming station
        roaming = await get_roaming_station(receiver=receiver, database=self.database)
        if roaming is None:
            # login command not found
            # return None to tell the push center to push notification for it.
            return None
        # 3. redirect message to roaming station
        return await self.redirect_message(msg=msg, neighbor=roaming)

    async def redirect_message(self, msg: ReliableMessage, neighbor: Optional[ID]) -> Optional[List[Content]]:
        """
        Redirect message to neighbor station

        :param msg:      network message
        :param neighbor: neighbor station
        :return: responses
        """
        """ Redirect message to neighbor station """
        assert neighbor is None or neighbor.type == EntityType.STATION, 'neighbor station ID error: %s' % neighbor
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
        if neighbor is not None and await session_push(msg=msg, receiver=neighbor) > 0:
            text = 'Message redirected.'
            cmd = ReceiptCommand.create(text=text, envelope=msg.envelope)
            cmd['neighbor'] = str(neighbor)
            return [cmd]
        # 2. push message to bridge
        return await bridge_message(msg=msg, neighbor=neighbor, bridge=current)


async def bridge_message(msg: ReliableMessage, neighbor: Optional[ID], bridge: ID) -> List[Content]:
    """
    Redirect message to neighbor station via the station bridge
    if neighbor is None, try to broadcast

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
    if neighbor is None:
        # broadcast to all neighbor stations
        # except that ones already in msg['recipients']
        await session_push(msg=msg, receiver=bridge)
        # no need to respond receipt for this broadcast message
        return []
    else:
        assert neighbor != bridge, 'cannot bridge cycled message: %s' % neighbor
        msg['neighbor'] = str(neighbor)
    # push to the bridge
    if await session_push(msg=msg, receiver=bridge) == 0:
        # station bridge not found
        Log.warning(msg='failed to push message to bridge: %s, drop message: %s -> %s'
                        % (bridge, msg.sender, msg.receiver))
        return []
    text = 'Message redirected via station bridge.'
    cmd = ReceiptCommand.create(text=text, envelope=msg.envelope)
    cmd['neighbor'] = str(neighbor)
    return [cmd]


async def session_push(msg: ReliableMessage, receiver: ID) -> int:
    """ push message via active session(s) of receiver """
    success = 0
    center = SessionCenter()
    active_sessions = center.active_sessions(identifier=receiver)
    for session in active_sessions:
        if await session.send_reliable_message(msg=msg):
            success += 1
    return success


async def get_roaming_station(receiver: ID, database: SessionDBI) -> Optional[ID]:
    """ get login command for roaming station """
    cmd, msg = await database.get_login_command_message(user=receiver)
    if isinstance(cmd, LoginCommand):
        station = cmd.station
        assert isinstance(station, dict), 'login command error: %s' % cmd
        return ID.parse(identifier=station.get('ID'))
