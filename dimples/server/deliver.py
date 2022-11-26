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
from typing import Optional, List, Set

from dimsdk import EntityType, ID
from dimsdk import Content
from dimsdk import ReliableMessage

from ..utils import Logging
from ..utils import Runner
from ..conn.session import get_sig


class DeliverTask:

    def __init__(self, msg: ReliableMessage, rcpt: Set[ID]):
        super().__init__()
        self.msg = msg
        self.rcpt = rcpt


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


class Deliver(Runner, Logging, ABC):

    def __init__(self):
        super().__init__()
        self.__queue = DeliverQueue()  # locked queue

    def __append(self, msg: ReliableMessage, rcpt: Set[ID]):
        task = DeliverTask(msg=msg, rcpt=rcpt)
        self.__queue.append(task=task)

    def __next(self) -> (Optional[ReliableMessage], Optional[Set[ID]]):
        task = self.__queue.next()
        if task is None:
            return None, None
        else:
            return task.msg, task.rcpt

    @abstractmethod
    def _get_recipients(self, receiver: ID) -> Set[ID]:
        """
        Get actual receivers

            1. neighbor stations
            2. group assistants
            3. bots

        :param receiver: original receiver in message
        :return: actual receivers
        """
        raise NotImplemented

    @abstractmethod
    def _respond(self, msg: ReliableMessage, rcpt: Set[ID]) -> List[Content]:
        """
        Respond receipt command for delivering

        :param msg:  original message
        :param rcpt: actual receivers
        :return: responses
        """
        raise NotImplemented

    def deliver_message(self, msg: ReliableMessage, receiver: ID) -> List[Content]:
        sender = msg.sender
        # get all actual recipients
        recipients = self._get_recipients(receiver=receiver)
        self.info(msg='delivering message (%s) from %s to %s, actual receivers: %s'
                      % (get_sig(msg=msg), sender, receiver, ID.revert(recipients)))
        self.__append(msg=msg, rcpt=recipients)
        # respond
        if sender.type == EntityType.STATION:
            # no need to respond receipt to station
            return []
        else:
            return self._respond(msg=msg, rcpt=recipients)

    # Override
    def process(self) -> bool:
        msg, recipients = self.__next()
        if msg is None:  # or recipients is None:
            # nothing to do
            return False
        try:
            sig = get_sig(msg=msg)
            traces = msg.get('traces')
            assert traces is not None, 'message (%s) traces should have been set by filter.' % sig
            # push to all recipients
            for receiver in recipients:
                if receiver in traces:
                    continue
                cnt = self._push_message(msg=msg, receiver=receiver)
                if cnt > 0 and receiver.type == EntityType.STATION:
                    # append station
                    traces.append(str(receiver))
                self.info(msg='message (%s) pushed to %s, %d session(s)' % (sig, receiver, cnt))
        except Exception as e:
            self.error(msg='process delivering (%s => %s) error: %s' % (msg.sender, recipients, e))
        # return True to process next immediately
        return True

    @abstractmethod
    def _push_message(self, msg: ReliableMessage, receiver: ID) -> int:
        """
        Push message to receiver

            1. save message;
            2. try to push via active session(s);
            3. push notification on session failed.

        :param msg:      network message
        :param receiver: actual receiver
        :return: success session count
        """
        raise NotImplemented

    def start(self):
        thread = threading.Thread(target=self.run, daemon=True)
        thread.start()


class Roamer(ABC):
    """ Deliver messages for roaming user """

    @abstractmethod
    def roam_message(self, msg: ReliableMessage, receiver: ID) -> bool:
        """
        Redirect message for other delivers

        :param msg:      received message
        :param receiver: actual receiver
        :return: True on redirected
        """
        raise NotImplemented

    @abstractmethod
    def roam_messages(self, messages: List[ReliableMessage], roaming: ID) -> int:
        """
        Redirect messages for dispatcher

        :param messages: cached messages
        :param roaming:  roaming station
        :return: True on redirected
        """
        raise NotImplemented
