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
    Common extensions for Messenger
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    Transform and send message
"""

from typing import Optional

# from startrek import DeparturePriority

from dimsdk import ID
from dimsdk import InstantMessage, ReliableMessage
from dimsdk import Content
from dimsdk import Messenger

from .transmitter import Transmitter


class CommonMessenger(Messenger, Transmitter):

    @property
    def transmitter(self) -> Transmitter:
        raise NotImplemented

    #
    #   Interfaces for Transmitting Message
    #

    # Override
    def send_content(self, sender: Optional[ID], receiver: ID, content: Content, priority: int) -> bool:
        transmitter = self.transmitter
        return transmitter.send_content(sender=sender, receiver=receiver, content=content, priority=priority)

    # Override
    def send_instant_message(self, msg: InstantMessage, priority: int) -> bool:
        transmitter = self.transmitter
        return transmitter.send_instant_message(msg=msg, priority=priority)

    # Override
    def send_reliable_message(self, msg: ReliableMessage, priority: int) -> bool:
        transmitter = self.transmitter
        return transmitter.send_reliable_message(msg=msg, priority=priority)
