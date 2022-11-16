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

from dimsdk import EntityType, ID
from dimsdk import Content
from dimsdk import ReliableMessage

from ..utils import Singleton
from ..utils import Logging
from ..utils import Runner
from ..common import ReceiptCommand
from ..common import SharedFacebook
from ..common import MessageDBI

from .session_server import SessionServer


@Singleton
class Dispatcher(Runner, Logging):

    def __init__(self):
        super().__init__()
        self.__database = None
        self.__queue: List[ReliableMessage] = []
        self.__lock = threading.Lock()

    @property
    def database(self) -> MessageDBI:
        return self.__database

    @database.setter
    def database(self, db: MessageDBI):
        self.__database = db

    def __append(self, msg: ReliableMessage):
        with self.__lock:
            self.__queue.append(msg)

    def __pop(self) -> Optional[ReliableMessage]:
        with self.__lock:
            if len(self.__queue) > 0:
                return self.__queue.pop(0)

    def deliver(self, msg: ReliableMessage) -> Optional[Content]:
        # check sender
        sender = msg.sender
        if sender.type == EntityType.STATION:
            # no need to respond receipt to station
            return None
        # append message to waiting queue
        self.__append(msg=msg)
        # check receiver
        receiver = msg.receiver
        if receiver.is_broadcast:
            text = 'Message broadcasting'
        elif receiver.is_group:
            text = 'Group Message delivering'
        else:
            text = 'Message delivering'
        # response
        return ReceiptCommand.response(text=text, msg=msg)

    def start(self):
        thread = threading.Thread(target=self.run, daemon=True)
        thread.start()

    # Override
    def process(self) -> bool:
        msg = self.__pop()
        if msg is None:
            # waiting queue is empty
            # wait a while to check again
            return False
        receiver = msg.receiver
        if receiver.is_broadcast:
            self.__deliver_broadcast_message(msg=msg)
        elif receiver.is_group:
            self.__deliver_group_message(msg=msg)
        else:
            self.__deliver_personal_message(msg=msg)
        # return True to get next task immediately
        return True

    def __deliver_broadcast_message(self, msg: ReliableMessage) -> int:
        # TODO: broadcast message
        self.info(msg='broadcasting message to: %s' % msg.receiver)
        return -1

    def __deliver_group_message(self, msg: ReliableMessage) -> int:
        db = self.database
        db.save_reliable_message(msg=msg)
        # redirect to group assistant
        group = msg.receiver
        facebook = SharedFacebook()
        assistants = facebook.assistants(identifier=group)
        if assistants is None:
            return 0
        cnt = 0
        for bot in assistants:
            self.info(msg='redirect group message to %s for %s' % (bot, group))
            cnt += push_message(msg=msg, receiver=bot)
        return cnt

    def __deliver_personal_message(self, msg: ReliableMessage) -> int:
        db = self.database
        db.save_reliable_message(msg=msg)
        # deliver message
        return push_message(msg=msg, receiver=msg.receiver)


def push_message(msg: ReliableMessage, receiver: ID) -> int:
    cnt = 0
    center = SessionServer()
    sessions = center.active_sessions(identifier=receiver)
    for sess in sessions:
        if sess.send_reliable_message(msg=msg):
            cnt += 1
    return cnt


# start as daemon
g_dispatcher = Dispatcher()
g_dispatcher.start()
