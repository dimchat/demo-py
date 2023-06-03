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
    Deliver Worker
    ~~~~~~~~~~~~~~

    Real worker
"""

import threading
from typing import Optional, List

from dimsdk import EntityType, ID
from dimsdk import ReliableMessage
from dkd import Content

from ..utils import Runner, Logging
from ..common import LoginCommand, ReceiptCommand
from ..common import CommonFacebook
from ..common import MessageDBI, SessionDBI

from .session_center import SessionCenter
from .dispatcher import Worker, Roamer
from .dispatcher import Dispatcher


class DeliverWorker(Worker, Logging):
    """ Real Worker """

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

    # Override
    def push_message(self, msg: ReliableMessage, receiver: ID) -> Optional[List[Content]]:
        """ Push message to receiver """
        assert receiver.is_user, 'receiver ID error: %s' % receiver
        if receiver.type == EntityType.STATION:
            # station won't roam to other station,
            # push message for it directly
            return self.redirect_message(msg=msg, neighbor=receiver)
        # try to push message directly
        if session_push(msg=msg, receiver=receiver) > 0:
            text = 'Message pushed'
            cmd = ReceiptCommand.create(text=text, msg=msg)
            return [cmd]
        # get roaming station
        roaming = get_roaming_station(receiver=receiver, database=self.database)
        if roaming is None:
            # login command not found
            return []
        else:
            return self.redirect_message(msg=msg, neighbor=roaming)

    # Override
    def redirect_message(self, msg: ReliableMessage, neighbor: ID) -> Optional[List[Content]]:
        """ Redirect message to neighbor station """
        assert neighbor.type == EntityType.STATION, 'neighbor station ID error: %s' % neighbor
        self.info(msg='redirect message %s => %s to neighbor station: %s' % (msg.sender, msg.receiver, neighbor))
        # 0. check current station
        current = self.facebook.current_user.identifier
        assert current.type == EntityType.STATION, 'current station ID error: %s' % current
        if neighbor == current:
            self.debug(msg='same destination: %s, msg %s => %s' % (neighbor, msg.sender, msg.receiver))
            # the user is roaming to current station, but it's not online now
            # return None to let the pusher to push notification for it.
            return None
        # 1. try to push message to neighbor station directly
        if session_push(msg=msg, receiver=neighbor) > 0:
            text = 'Message redirected to neighbor station'
            cmd = ReceiptCommand.create(text=text, msg=msg)
            cmd['neighbor'] = str(neighbor)
            return [cmd]
        # 2. push message to bridge
        return self.bridge_message(msg=msg, neighbor=neighbor, bridge=current)

    # noinspection PyMethodMayBeStatic
    def bridge_message(self, msg: ReliableMessage, neighbor: ID, bridge: ID) -> List[Content]:
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
            text = 'Message pushing to neighbor station via the bridge'
            cmd = ReceiptCommand.create(text=text, msg=msg)
            cmd['neighbor'] = str(neighbor)
            return [cmd]
        else:
            return []


def get_roaming_station(receiver: ID, database: SessionDBI) -> Optional[ID]:
    """ get login command for roaming station """
    cmd, msg = database.login_command_message(user=receiver)
    if isinstance(cmd, LoginCommand):
        station = cmd.station
        assert isinstance(station, dict), 'login command error: %s' % cmd
        return ID.parse(identifier=station.get('ID'))


def session_push(msg: ReliableMessage, receiver: ID) -> int:
    """ push message via active session(s) of receiver """
    success = 0
    center = SessionCenter()
    active_sessions = center.active_sessions(identifier=receiver)
    for session in active_sessions:
        if session.send_reliable_message(msg=msg):
            success += 1
    return success


#
#   Roamer
#

class RoamingInfo:

    def __init__(self, user: ID, station: ID):
        super().__init__()
        self.user = user
        self.station = station
        self.start_pos = 0


class DefaultRoamer(Runner, Roamer, Logging):
    """ Deliver messages for roaming user """

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

    # Override
    def add_roaming(self, user: ID, station: ID) -> bool:
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
        start = info.start_pos
        limit = 1024
        try:
            db = self.database
            cached_messages, remaining = db.reliable_messages(receiver=receiver, start=start, limit=limit)
            if remaining > 0:
                # there are remaining messages, push the roaming user back for next try
                info.start_pos = start + limit
                self.__append(info=info)
            elif cached_messages is None or len(cached_messages) == 0:
                self.debug(msg='no cached message for this user: %s' % receiver)
                return True
            # get deliver delegate for receiver
            dispatcher = Dispatcher()
            if receiver.type == EntityType.STATION:
                deliver = dispatcher.station_deliver
            elif receiver.type == EntityType.BOT:
                deliver = dispatcher.bot_deliver
            else:
                deliver = dispatcher.user_deliver
            # deliver cached messages one by one
            for msg in cached_messages:
                deliver.deliver_message(msg=msg, receiver=receiver)
        except Exception as e:
            self.error(msg='process roaming user (%s => %s) error: %s' % (receiver, roaming, e))
        # return True to process next immediately
        return True

    def start(self):
        thread = threading.Thread(target=self.run, daemon=True)
        thread.start()
