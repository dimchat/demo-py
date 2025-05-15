# -*- coding: utf-8 -*-
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

import threading
from typing import List, Dict

from dimsdk import InstantMessage, ReliableMessage

from ..utils import Logging


class SuspendedMessageQueue(Logging):
    """
        Message Waiting List
        ~~~~~~~~~~~~~~~~~~~~
    """

    def __init__(self, capacity: int = 32):
        super().__init__()
        self.__capacity = capacity
        # suspended messages
        self.__suspend_lock = threading.Lock()
        self.__incoming_messages: List[ReliableMessage] = []
        self.__outgoing_messages: List[InstantMessage] = []

    def suspend_reliable_message(self, msg: ReliableMessage, error: Dict):
        """
        Add income message in a queue for waiting sender's visa

        :param msg:   incoming message
        :param error: error info
        """
        self.warning(msg='suspend message: %s -> %s, %s' % (msg.sender, msg.receiver, error))
        msg['error'] = error
        with self.__suspend_lock:
            if len(self.__incoming_messages) > self.__capacity:
                self.__incoming_messages.pop(0)
            self.__incoming_messages.append(msg)

    def suspend_instant_message(self, msg: InstantMessage, error: Dict):
        """
        Add outgo message in a queue for waiting receiver's visa

        :param msg:   outgo message
        :param error: error info
        """
        self.warning(msg='suspend message: %s -> %s, %s' % (msg.sender, msg.receiver, error))
        msg['error'] = error
        with self.__suspend_lock:
            if len(self.__outgoing_messages) > self.__capacity:
                self.__outgoing_messages.pop(0)
            self.__outgoing_messages.append(msg)

    def resume_reliable_messages(self) -> List[ReliableMessage]:
        with self.__suspend_lock:
            messages = self.__incoming_messages
            self.__incoming_messages = []
            return messages

    def resume_instant_messages(self) -> List[InstantMessage]:
        with self.__suspend_lock:
            messages = self.__outgoing_messages
            self.__outgoing_messages = []
            return messages
