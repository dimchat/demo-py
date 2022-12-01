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
from typing import Optional, List, Dict, Set

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
class PushCenter(Runner, Logging):

    def __init__(self):
        super().__init__()
        self.__services = set()
        # push task
        self.__tasks: List[PushTask] = []
        self.__task_lock = threading.Lock()
        # badges count
        self.__badges: Dict[ID, int] = {}
        self.__badge_lock = threading.Lock()

    def add_service(self, service: PushService):
        """ add service handler """
        self.__services.add(service)

    def remove_service(self, service: PushService):
        """ remove service handler """
        self.__services.remove(service)

    def reset_badge(self, identifier: ID):
        """ clear badge for user """
        with self.__badge_lock:
            self.__badges.pop(identifier, None)

    def __increase_badge(self, identifier: ID) -> int:
        """ get self-increasing badge """
        with self.__badge_lock:
            num = self.__badges.get(identifier, 0) + 1
            self.__badges[identifier] = num
            return num

    def __append(self, task: PushTask):
        with self.__task_lock:
            # check overflow
            count = len(self.__tasks)
            if count > 65535:
                self.warning(msg='waiting queue in PushCenter is too long: %d' % count)
                if count > 100000:
                    # drop half tasks waiting too long
                    self.__tasks = self.__tasks[-50000:]
            # OK, append it to tail
            self.__tasks.append(task)

    def __pop(self) -> Optional[PushTask]:
        with self.__task_lock:
            if len(self.__tasks) > 0:
                return self.__tasks.pop(0)

    def add_notification(self, sender: ID, receiver: ID, info: PushInfo = None,
                         title: str = None, content: str = None, image: str = None,
                         badge: int = -1, sound: str = None):
        """
        Append push info to a waiting queue

        :param sender:   message sender
        :param receiver: message receiver
        :param info:     push info (includes title, content, image, badge, sound)
        :param title:
        :param content:
        :param image:
        :param badge:    -1 means let the PushCenter to manage; 0 means no badge
        :param sound:
        :return: False on error
        """
        if info is None:
            # create push info with title, content, image, badge, sound
            info = PushInfo.create(title=title, content=content, image=image, badge=badge, sound=sound)
        task = PushTask(sender=sender, receiver=receiver, info=info)
        self.__append(task=task)
        return True

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
        # check badge
        if badge < 0:
            badge = self.__increase_badge(identifier=receiver)
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
