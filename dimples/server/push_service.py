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
    Push Notification service
    ~~~~~~~~~~~~~~~~~~~~~~~~~
"""

import threading
from abc import ABC, abstractmethod
from typing import Optional, List, Set

from dimsdk import ID

from ..utils import Singleton
from ..utils import Logging
from ..utils import Runner

from .push_info import PushInfo


class PushService(ABC):

    @abstractmethod
    def push_notification(self, sender: ID, receiver: ID, info: PushInfo = None,
                          title: str = None, content: str = None, image: str = None,
                          badge: int = 0, sound: str = None):
        """
        Push notification info from sender to receiver

        :param sender:   from
        :param receiver: to
        :param info:     notification info(title, content, image, badge, sound
        :param title:    title text
        :param content:  body text
        :param image:    image URL
        :param badge:    unread count
        :param sound:    sound URL
        """
        raise NotImplemented


class PushTask:

    def __init__(self, sender: ID, receiver: ID, info: PushInfo):
        super().__init__()
        self.__sender = sender
        self.__receiver = receiver
        self.__info = info

    @property
    def sender(self) -> ID:
        return self.__sender

    @property
    def receiver(self) -> ID:
        return self.__receiver

    @property
    def info(self) -> PushInfo:
        return self.__info


@Singleton
class PushCenter(Runner, Logging, PushService):

    def __init__(self):
        super().__init__()
        self.__services = set()
        self.__tasks: List[PushTask] = []
        self.__lock = threading.Lock()

    def add_service(self, service: PushService):
        """ add service handler """
        self.__services.add(service)

    def remove_service(self, service: PushService):
        """ remove service handler """
        self.__services.remove(service)

    def __append(self, task: PushTask):
        with self.__lock:
            self.__tasks.append(task)

    def __pop(self) -> Optional[PushTask]:
        with self.__lock:
            if len(self.__tasks) > 0:
                return self.__tasks.pop(0)

    def __count(self) -> int:
        with self.__lock:
            return len(self.__tasks)

    def start(self):
        thread = threading.Thread(target=self.run, daemon=True)
        thread.start()

    # Override
    def process(self) -> bool:
        task = self.__pop()
        if task is None:
            # waiting queue is empty
            # wait a while to check again
            return False
        # parameters
        sender = task.sender
        receiver = task.receiver
        info = task.info
        title = info.title
        content = info.content
        image = info.image
        badge = info.badge
        sound = info.sound
        # try all services
        services: Set[PushService] = set(self.__services)
        self.debug(msg='pushing from %s to %s: %s, count: %d' % (sender, receiver, content, len(services)))
        for handler in services:
            try:
                handler.push_notification(sender=sender, receiver=receiver, info=info,
                                          title=title, content=content, image=image,
                                          badge=badge, sound=sound)
            except Exception as e:
                self.error(msg='push error: %s, from %s to %s: %s' % (e, sender, receiver, info))
        # return True to get next task immediately
        return True

    #
    #   PushService
    #

    # Override
    def push_notification(self, sender: ID, receiver: ID, info: PushInfo = None,
                          title: str = None, content: str = None, image: str = None,
                          badge: int = 0, sound: str = None):
        count = self.__count()
        if count > 65535:
            self.warning(msg='waiting queue is too long: %d' % count)
            if count > 100000:
                return False
        # build push info and append to a waiting queue
        if info is None:
            info = PushInfo.create(title=title, content=content, image=image, badge=badge, sound=sound)
        task = PushTask(sender=sender, receiver=receiver, info=info)
        self.__append(task=task)
        return True


# start as daemon
g_center = PushCenter()
g_center.start()
