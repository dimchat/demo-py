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

from abc import ABC, abstractmethod

from dimsdk import ID
from dimsdk import ReliableMessage

from ..utils import Logging
from ..common import SharedFacebook

from .session_center import SessionCenter
from .pusher import Pusher, DefaultPusher


class Deliver(ABC):

    @abstractmethod
    def deliver_message(self, msg: ReliableMessage) -> int:
        raise NotImplemented


class BroadcastDeliver(Deliver, Logging):

    # Override
    def deliver_message(self, msg: ReliableMessage) -> int:
        # TODO: broadcast message
        self.info(msg='broadcasting message to: %s' % msg.receiver)
        return -1


class GroupDeliver(Deliver, Logging):

    # Override
    def deliver_message(self, msg: ReliableMessage) -> int:
        # redirect to group assistant
        group = msg.receiver
        facebook = SharedFacebook()
        assistants = facebook.assistants(identifier=group)
        if assistants is None:
            return -1
        cnt = 0
        for bot in assistants:
            self.info(msg='redirect group message to %s for %s' % (bot, group))
            cnt += session_push(msg=msg, receiver=bot)
        return cnt


class DefaultDeliver(Deliver, Logging):

    def __init__(self):
        super().__init__()
        self.__pusher = DefaultPusher()

    @property
    def pusher(self) -> Pusher:
        return self.__pusher

    @pusher.setter
    def pusher(self, delegate: Pusher):
        self.__pusher = delegate

    # Override
    def deliver_message(self, msg: ReliableMessage) -> int:
        # 1. push message to the waiting queue of receiver's session(s)
        receiver = msg.receiver
        cnt = session_push(msg=msg, receiver=receiver)
        if cnt > 0:
            # success
            sig = msg.get('signature')
            sig = sig[-8:]  # last 6 bytes (signature in base64)
            self.info(msg='Message (%s) pushed to %d session(s)' % (sig, cnt))
        else:
            # no session active, try push notification
            delegate = self.pusher
            if delegate is None:
                self.warning(msg='pusher not set yet, drop notification for: %s' % receiver)
            else:
                delegate.push_notification(msg=msg)
        return cnt


def session_push(msg: ReliableMessage, receiver: ID) -> int:
    cnt = 0
    center = SessionCenter()
    sessions = center.active_sessions(identifier=receiver)
    for sess in sessions:
        if sess.send_reliable_message(msg=msg):
            cnt += 1
    return cnt
