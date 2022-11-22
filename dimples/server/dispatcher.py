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
from typing import Optional, List

from dimsdk import ID
from dimsdk import Content
from dimsdk import ReliableMessage

from ..utils import Singleton, Logging, Runner
from ..common import MessageDBI, CommonFacebook

from .session_center import SessionCenter
from .deliver import Deliver


class RoamingInfo:

    def __init__(self, user: ID, station: ID):
        super().__init__()
        self.user = user
        self.station = station


@Singleton
class Dispatcher(Runner, Logging):

    def __init__(self):
        super().__init__()
        self.__database: Optional[MessageDBI] = None
        self.__facebook: Optional[CommonFacebook] = None
        # roaming (user id, station id)
        self.__roaming: List[RoamingInfo] = []
        self.__lock = threading.Lock()
        # deliver delegates
        self.__deliver: Optional[Deliver] = None
        self.__group_deliver: Optional[Deliver] = None
        self.__broadcast_deliver: Optional[Deliver] = None

    @property
    def database(self) -> MessageDBI:
        return self.__database

    @database.setter
    def database(self, db: MessageDBI):
        self.__database = db

    @property
    def facebook(self) -> CommonFacebook:
        return self.__facebook

    @facebook.setter
    def facebook(self, barrack: facebook):
        self.__facebook = barrack

    def __append(self, info: RoamingInfo):
        with self.__lock:
            self.__roaming.append(info)

    def __next(self) -> Optional[RoamingInfo]:
        with self.__lock:
            if len(self.__roaming) > 0:
                return self.__roaming.pop(0)

    def add_roaming(self, user: ID, station: ID):
        info = RoamingInfo(user=user, station=station)
        self.__append(info=info)

    # Override
    def process(self) -> bool:
        info = self.__next()
        if info is None:
            # nothing to do
            return False
        db = self.database
        cached_messages = db.reliable_messages(receiver=info.user)
        if cached_messages is None or len(cached_messages) == 0:
            # no cached message for this user
            return True
        # redirect cached messages to the roaming station
        current = self.facebook.current_user
        messages_roam(messages=cached_messages, roaming=info.station, current=current.identifier)
        # return True to process next immediately
        return True

    def start(self):
        thread = threading.Thread(target=self.run, daemon=True)
        thread.start()
        # start deliver delegates
        deliver = self.deliver
        if deliver is not None:
            deliver.start()
        deliver = self.group_deliver
        if deliver is not None:
            deliver.start()
        deliver = self.broadcast_deliver
        if deliver is not None:
            deliver.start()

    # Override
    def stop(self):
        super().stop()
        # stop deliver delegates
        deliver = self.deliver
        if deliver is not None:
            deliver.stop()
        deliver = self.group_deliver
        if deliver is not None:
            deliver.stop()
        deliver = self.broadcast_deliver
        if deliver is not None:
            deliver.stop()

    #
    #   Deliver delegates
    #

    @property
    def deliver(self) -> Deliver:
        return self.__deliver

    @deliver.setter
    def deliver(self, delegate: Deliver):
        self.__deliver = delegate

    @property
    def group_deliver(self) -> Deliver:
        return self.__group_deliver

    @group_deliver.setter
    def group_deliver(self, delegate: Deliver):
        self.__group_deliver = delegate

    @property
    def broadcast_deliver(self) -> Deliver:
        return self.__broadcast_deliver

    @broadcast_deliver.setter
    def broadcast_deliver(self, delegate: Deliver):
        self.__broadcast_deliver = delegate

    def deliver_message(self, msg: ReliableMessage) -> List[Content]:
        receiver = msg.receiver
        if receiver.is_broadcast:
            return self.broadcast_deliver.deliver_message(msg=msg)
        elif receiver.is_group:
            return self.group_deliver.deliver_message(msg=msg)
        else:
            return self.deliver.deliver_message(msg=msg)


def messages_roam(messages: List[ReliableMessage], roaming: ID, current: ID):
    """ deliver messages to roaming station """
    center = SessionCenter()
    failed = []
    # 1. redirect cached messages to roaming station directly
    sessions = center.active_sessions(identifier=roaming)
    for msg in messages:
        sent = False
        for sess in sessions:
            if sess.send_reliable_message(msg=msg, priority=1):
                # deliver to first active session of roaming station,
                # actually there is only one session for one neighbour
                sent = True
                break
        if not sent:
            failed.append(msg)
    if len(failed) == 0:
        # all cached messages have bean sent to the roaming station directly
        return True
    # 2. roaming station not connected, redirect it via station bridge
    sessions = center.active_sessions(identifier=current)
    for msg in failed:
        # set roaming station ID here to let the bridge know where to go,
        # and the bridge should remove 'roaming' before deliver it.
        msg['roaming'] = str(roaming)
        for sess in sessions:
            if sess.send_reliable_message(msg=msg, priority=1):
                # deliver to first active session of station bridge,
                # actually there is only one session for the bridge
                break
