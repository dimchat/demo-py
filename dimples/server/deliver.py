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
    Message Deliver
    ~~~~~~~~~~~~~~~

    A deliver to decide which way to redirect message.
"""

import threading
from abc import ABC, abstractmethod
from typing import Optional, List, Tuple

from dimsdk import EntityType, ID
from dimsdk import Content
from dimsdk import ReliableMessage

from ..utils import Logging
from ..utils import Runner
from ..common import MessageDBI

from .pusher import Pusher
from .dispatcher import Deliver
from .dispatcher import Dispatcher


class DeliverTask:

    def __init__(self, msg: ReliableMessage, receiver: ID):
        super().__init__()
        self.msg = msg
        self.receiver = receiver


class DeliverQueue:

    def __init__(self):
        super().__init__()
        # locked queue
        self.__tasks: List[DeliverTask] = []
        self.__lock = threading.Lock()

    def append(self, task: DeliverTask):
        with self.__lock:
            self.__tasks.append(task)

    def next(self) -> Optional[DeliverTask]:
        with self.__lock:
            if len(self.__tasks) > 0:
                return self.__tasks.pop(0)


class BaseDeliver(Runner, Deliver, Logging, ABC):

    def __init__(self):
        super().__init__()
        self.__queue = DeliverQueue()  # locked queue

    def __append(self, msg: ReliableMessage, receiver: ID):
        task = DeliverTask(msg=msg, receiver=receiver)
        self.__queue.append(task=task)

    def __next(self) -> Tuple[Optional[ReliableMessage], Optional[ID]]:
        task = self.__queue.next()
        if task is None:
            return None, None
        else:
            return task.msg, task.receiver

    # Override
    def deliver_message(self, msg: ReliableMessage, receiver: ID) -> List[Content]:
        assert receiver.is_user and not receiver.is_broadcast, 'receiver error: %s' % receiver
        self.__append(msg=msg, receiver=receiver)
        return []

    # Override
    def process(self) -> bool:
        msg, receiver = self.__next()
        if msg is None:  # or recipients is None:
            # nothing to do
            return False
        try:
            responses = self._dispatch(msg=msg, receiver=receiver)
            self._respond(responses=responses, msg=msg)
        except Exception as e:
            self.error(msg='process delivering (%s => %s) error: %s' % (msg.sender, receiver, e))
        # return True to process next immediately
        return True

    def _respond(self, responses: Optional[List[Content]], msg: ReliableMessage):
        # TODO: send responses to msg.receiver
        pass

    @abstractmethod
    def _dispatch(self, msg: ReliableMessage, receiver: ID) -> Optional[List[Content]]:
        """ deliver message by dispatcher """
        raise NotImplemented

    def start(self):
        thread = threading.Thread(target=self.run, daemon=True)
        thread.start()


class StationDeliver(BaseDeliver):

    # Override
    def _dispatch(self, msg: ReliableMessage, receiver: ID) -> Optional[List[Content]]:
        assert receiver.type == EntityType.STATION, 'station ID error: %s' % receiver
        dispatcher = Dispatcher()
        worker = dispatcher.deliver_worker
        return worker.redirect_message(msg=msg, neighbor=receiver)


class BotDeliver(BaseDeliver):

    def __init__(self, database: MessageDBI):
        super().__init__()
        self.__database = database

    @property
    def database(self) -> MessageDBI:
        return self.__database

    # Override
    def _dispatch(self, msg: ReliableMessage, receiver: ID) -> Optional[List[Content]]:
        assert receiver.type == EntityType.BOT, 'bot ID error: %s' % receiver
        # 1. save message for group assistant
        save_message(msg=msg, receiver=receiver, database=self.database)
        # 2. push message
        dispatcher = Dispatcher()
        worker = dispatcher.deliver_worker
        return worker.push_message(msg=msg, receiver=receiver)


class UserDeliver(BaseDeliver):

    def __init__(self, database: MessageDBI, pusher: Pusher = None):
        super().__init__()
        self.__database = database
        self.__pusher = pusher

    @property
    def database(self) -> MessageDBI:
        return self.__database

    @property
    def pusher(self) -> Optional[Pusher]:
        return self.__pusher

    # Override
    def _dispatch(self, msg: ReliableMessage, receiver: ID) -> Optional[List[Content]]:
        assert receiver.is_user, 'user ID error: %s' % receiver
        assert receiver.type != EntityType.STATION, 'user ID error: %s' % receiver
        assert receiver.type != EntityType.BOT, 'user ID error: %s' % receiver
        # 1. save message for receiver
        save_message(msg=msg, receiver=receiver, database=self.database)
        # 2. push message
        dispatcher = Dispatcher()
        worker = dispatcher.deliver_worker
        responses = worker.push_message(msg=msg, receiver=receiver)
        if responses is not None:
            # pushed to active session, or redirect to neighbor station
            return responses
        # 3. push notification
        pusher = self.pusher
        if pusher is None:
            self.warning(msg='pusher not set yet, drop notification for: %s' % receiver)
        else:
            pusher.push_notification(msg=msg)


def save_message(msg: ReliableMessage, receiver: ID, database: MessageDBI) -> bool:
    if receiver.type == EntityType.STATION or msg.sender.type == EntityType.STATION:
        # no need to save station message
        return False
    return database.save_reliable_message(msg=msg, receiver=receiver)
