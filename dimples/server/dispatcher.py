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
from ..common import MessageDBI

from .deliver import Deliver, Roamer


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
        # roaming (user id => station id)
        self.__roaming_queue: List[RoamingInfo] = []
        self.__roaming_lock = threading.Lock()
        self.__roaming_deliver: Optional[Roamer] = None
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

    def __append(self, info: RoamingInfo):
        with self.__roaming_lock:
            self.__roaming_queue.append(info)

    def __next(self) -> Optional[RoamingInfo]:
        with self.__roaming_lock:
            if len(self.__roaming_queue) > 0:
                return self.__roaming_queue.pop(0)

    def add_roaming(self, user: ID, station: ID):
        info = RoamingInfo(user=user, station=station)
        self.__append(info=info)

    # Override
    def process(self) -> bool:
        info = self.__next()
        if info is None:
            # nothing to do
            return False
        receiver = info.user
        roaming = info.station
        db = self.database
        try:
            cached_messages = db.reliable_messages(receiver=receiver)
            if cached_messages is None or len(cached_messages) == 0:
                self.debug(msg='no cached message for this user: %s' % receiver)
                return True
            # redirect cached messages to the roaming station
            roamer = self.roaming_deliver
            if roamer is None:
                self.error(msg='roamer not found for receiver: %s' % receiver)
            else:
                roamer.roam_messages(messages=cached_messages, roaming=roaming)
        except Exception as e:
            self.error(msg='process roaming user (%s => %s) error: %s' % (receiver, roaming, e))
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

    @property
    def roaming_deliver(self) -> Roamer:
        return self.__roaming_deliver

    @roaming_deliver.setter
    def roaming_deliver(self, delegate: Roamer):
        self.__roaming_deliver = delegate

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

    def deliver_message(self, msg: ReliableMessage, receiver: ID) -> List[Content]:
        if receiver.is_broadcast:
            deliver = self.broadcast_deliver
        elif receiver.is_group:
            deliver = self.group_deliver
        else:
            deliver = self.deliver
        if deliver is None:
            self.error(msg='deliver not found for message: %s => %s' % (msg.sender, receiver))
        else:
            return deliver.deliver_message(msg=msg, receiver=receiver)
