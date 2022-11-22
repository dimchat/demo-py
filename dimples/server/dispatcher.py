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

from typing import Optional, List

from dimsdk import Content
from dimsdk import ReliableMessage

from ..utils import Singleton

from .deliver import Deliver


@Singleton
class Dispatcher:

    def __init__(self):
        super().__init__()
        self.__deliver: Optional[Deliver] = None
        self.__group_deliver: Optional[Deliver] = None
        self.__broadcast_deliver: Optional[Deliver] = None

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

    def start(self):
        deliver = self.deliver
        if deliver is not None:
            deliver.start()
        deliver = self.group_deliver
        if deliver is not None:
            deliver.start()
        deliver = self.broadcast_deliver
        if deliver is not None:
            deliver.start()

    def stop(self):
        deliver = self.deliver
        if deliver is not None:
            deliver.stop()
        deliver = self.group_deliver
        if deliver is not None:
            deliver.stop()
        deliver = self.broadcast_deliver
        if deliver is not None:
            deliver.stop()
