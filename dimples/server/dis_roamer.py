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

from ..utils import Logging, Runner
from ..common import MessageDBI
from ..common import ReliableMessageDBI

from .deliver import MessageDeliver


class RoamingInfo:

    def __init__(self, user: ID, station: ID):
        super().__init__()
        self.user = user
        self.station = station


class Roamer(Runner, Logging):
    """ Delegate for redirect cached messages to roamed station """

    def __init__(self, database: MessageDBI, deliver: MessageDeliver):
        super().__init__(interval=Runner.INTERVAL_SLOW)
        self.__database = database
        self.__deliver = deliver
        # roaming (user id => station id)
        self.__queue: List[RoamingInfo] = []
        self.__lock = threading.Lock()

    @property
    def database(self) -> MessageDBI:
        return self.__database

    @property
    def deliver(self) -> MessageDeliver:
        return self.__deliver

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
        else:
            db = self.database
            deliver = self.deliver
        # get roamer info
        receiver = info.user
        roaming = info.station
        limit = ReliableMessageDBI.CACHE_LIMIT
        try:
            cached_messages = await db.get_reliable_messages(receiver=receiver, limit=limit)
            self.debug(msg='got %d cached messages for roaming user: %s' % (len(cached_messages), receiver))
            # deliver cached messages one by one
            for msg in cached_messages:
                await deliver.push_message(msg=msg, receiver=receiver)
        except Exception as e:
            self.error(msg='process roaming user (%s => %s) error: %s' % (receiver, roaming, e))
        # return True to process next immediately
        return True
