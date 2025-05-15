# -*- coding: utf-8 -*-
#
#   DIM-SDK : Decentralized Instant Messaging Software Development Kit
#
# ==============================================================================
# MIT License
#
# Copyright (c) 2023 Albert Moky
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
    Push Notification service
    ~~~~~~~~~~~~~~~~~~~~~~~~~
"""

import threading
import time
from abc import ABC, abstractmethod
from typing import Optional, List, Dict

from dimsdk import ID, ReliableMessage

from ..utils import Runner
from ..utils import Singleton, Logging


class PushQueue(Logging):

    def __init__(self):
        super().__init__()
        self.__messages: Optional[List[ReliableMessage]] = None
        self.__expired = 0
        self.__lock = threading.Lock()

    def add_message(self, msg: ReliableMessage):
        with self.__lock:
            if self.__messages is None:
                self.__messages = [msg]
                self.__expired = time.time() + 1  # process after a while
                return 1
            # check overflow
            count = len(self.__messages)
            if count > 65535:
                self.warning(msg='waiting queue in PushCenter is too long: %d' % count)
                if count > 100000:
                    # drop half tasks waiting too long
                    self.__messages = self.__messages[-50000:]
                    count = 50000
            # OK, append it to tail
            self.__messages.append(msg)
            return count + 1

    def get_messages(self) -> Optional[List[ReliableMessage]]:
        with self.__lock:
            array = self.__messages
            if array is None:
                # no message waiting
                return None
            now = time.time()
            if now < self.__expired:
                # wait a while
                return None
            # times up
            if len(array) <= 50:
                self.__messages = None
            else:
                # too more messages, process them in batch
                self.__messages = array[50:]
                array = array[:50]
            return array


class BadgeKeeper:

    def __init__(self):
        super().__init__()
        self.__badges: Dict[ID, int] = {}
        self.__lock = threading.Lock()

    def increase_badge(self, identifier: ID) -> int:
        """ get self-increasing badge """
        with self.__lock:
            count = self.__badges.get(identifier, 0) + 1
            self.__badges[identifier] = count
            return count

    def reset_badge(self, identifier: ID):
        """ clear badge for user """
        with self.__lock:
            self.__badges.pop(identifier, None)


class PushService(ABC):

    @abstractmethod
    async def process(self, messages: List[ReliableMessage], badge_keeper: BadgeKeeper) -> bool:
        """ build and push notification for a batch of messages """
        raise NotImplemented


@Singleton
class PushCenter(Runner, Logging):

    def __init__(self):
        super().__init__(interval=Runner.INTERVAL_SLOW)
        self.__queue = PushQueue()
        self.__keeper = BadgeKeeper()
        self.__service: Optional[PushService] = None
        # auto start
        self.start()

    @property
    def service(self) -> Optional[PushService]:
        return self.__service

    @service.setter
    def service(self, pusher: PushService):
        self.__service = pusher

    @property
    def badge_keeper(self) -> BadgeKeeper:
        return self.__keeper

    def reset_badge(self, identifier: ID):
        """ clear badge for user """
        keeper = self.__keeper
        keeper.reset_badge(identifier=identifier)

    def push_notification(self, msg: ReliableMessage):
        """ Push notification for msg receiver """
        queue = self.__queue
        queue.add_message(msg=msg)

    def start(self):
        thr = Runner.async_thread(coro=self.run())
        thr.start()
        # Runner.async_task(coro=self.run())

    # Override
    async def process(self) -> bool:
        # 1. get waiting messages
        queue = self.__queue
        messages = queue.get_messages()
        if messages is None:
            # nothing to do now, return False to have a rest
            return False
        # 2. get message processor
        service = self.__service
        if service is None:
            self.error(msg='push service not found')
            return False
        # 3. process
        return await service.process(messages=messages, badge_keeper=self.badge_keeper)
