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

from dimsdk import ReliableMessage

from ..utils import Singleton
from ..utils import Logging
from ..utils import Runner

from .deliver import Deliver


@Singleton
class Dispatcher(Runner, Deliver, Logging):

    def __init__(self):
        super().__init__()
        self.__deliver: Optional[Deliver] = None
        self.__group_deliver: Optional[Deliver] = None
        self.__broadcast_deliver: Optional[Deliver] = None
        # locked message queue
        self.__messages: List[ReliableMessage] = []
        self.__lock = threading.Lock()

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

    #
    #   Message Queue
    #

    def __append(self, msg: ReliableMessage):
        with self.__lock:
            self.__messages.append(msg)

    def __pop(self) -> Optional[ReliableMessage]:
        with self.__lock:
            if len(self.__messages) > 0:
                return self.__messages.pop(0)

    # Override
    def deliver_message(self, msg: ReliableMessage) -> int:
        # append message to waiting queue
        self.__append(msg=msg)
        return 0

    def start(self):
        thread = threading.Thread(target=self.run, daemon=True)
        thread.start()

    # Override
    def process(self) -> bool:
        # 1. get next message
        msg = self.__pop()
        if msg is None:
            # waiting queue is empty
            # wait a while to check again
            return False
        # 2. get deliver for this message
        receiver = msg.receiver
        if receiver.is_broadcast:
            deliver = self.broadcast_deliver
        elif receiver.is_group:
            deliver = self.group_deliver
        else:
            deliver = self.deliver
        # 3. try to deliver
        try:
            assert isinstance(deliver, Deliver), 'deliver error: %s' % deliver
            deliver.deliver_message(msg=msg)
            # return True to get next task immediately
            return True
        except Exception as e:
            self.error(msg='failed to deliver message: %s, %s => %s' % (e, msg.sender, receiver))
