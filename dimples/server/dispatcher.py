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
from dimsdk import ContentType, Content
from dimsdk import ReliableMessage

from ..utils import Singleton
from ..utils import Logging
from ..utils import Runner
from ..common import ReceiptCommand
from ..common import SharedFacebook
from ..common import MessageDBI

from .session_center import SessionCenter
from .push_service import PushCenter


@Singleton
class Dispatcher(Runner, Logging):

    def __init__(self):
        super().__init__()
        self.__database = None
        self.__messages: List[ReliableMessage] = []
        self.__lock = threading.Lock()

    @property
    def database(self) -> MessageDBI:
        return self.__database

    @database.setter
    def database(self, db: MessageDBI):
        self.__database = db

    def __append(self, msg: ReliableMessage):
        with self.__lock:
            self.__messages.append(msg)

    def __pop(self) -> Optional[ReliableMessage]:
        with self.__lock:
            if len(self.__messages) > 0:
                return self.__messages.pop(0)

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
        return ReceiptCommand.create(text=text, msg=msg)

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
        assistants = g_facebook.assistants(identifier=group)
        if assistants is None:
            return 0
        cnt = 0
        for bot in assistants:
            self.info(msg='redirect group message to %s for %s' % (bot, group))
            cnt += session_push(msg=msg, receiver=bot)
        return cnt

    def __deliver_personal_message(self, msg: ReliableMessage) -> int:
        db = self.database
        db.save_reliable_message(msg=msg)
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
            pns_push(msg=msg, receiver=receiver)
        return cnt


def session_push(msg: ReliableMessage, receiver: ID) -> int:
    cnt = 0
    center = SessionCenter()
    sessions = center.active_sessions(identifier=receiver)
    for sess in sessions:
        if sess.send_reliable_message(msg=msg):
            cnt += 1
    return cnt


def pns_push(msg: ReliableMessage, receiver: ID) -> str:
    """ PNs: push notification for msg """
    sender = msg.sender
    group = msg.group
    msg_type = msg.type
    # 1. check original sender, group & msg type
    if msg_type is None:
        msg_type = 0
    elif msg_type == ContentType.FORWARD:
        # check origin message info (group message separated by assistant)
        origin = msg.get('origin')
        if isinstance(origin, dict):
            value = ID.parse(identifier=origin.get('sender'))
            if value is not None:
                sender = value
            value = ID.parse(identifier=origin.get('group'))
            if value is not None:
                group = value
            value = origin.get('type')
            if value is not None:
                msg_type = value
            msg.pop('origin')
    # TODO: 2. check mute-list
    # ...
    # 3. build push message
    text = pns_build_message(sender=sender, receiver=receiver, group=group, msg_type=msg_type, msg=msg)
    if text is None:
        # ignore msg type
        return 'Message cached.'
    else:
        # push notification
        center = PushCenter()
        center.push_notification(sender=sender, receiver=receiver, content=text)
        return 'Message pushed.'


# noinspection PyUnusedLocal
def pns_build_message(sender: ID, receiver: ID, group: ID, msg_type: int, msg: ReliableMessage) -> Optional[str]:
    """ PNs: build text message for msg """
    if msg_type == 0:
        something = 'a message'
    elif msg_type == ContentType.TEXT:
        something = 'a text message'
    elif msg_type == ContentType.FILE:
        something = 'a file'
    elif msg_type == ContentType.IMAGE:
        something = 'an image'
    elif msg_type == ContentType.AUDIO:
        something = 'a voice message'
    elif msg_type == ContentType.VIDEO:
        something = 'a video'
    elif msg_type in [ContentType.MONEY, ContentType.TRANSFER]:
        something = 'some money'
    else:
        return None
    from_name = get_name(identifier=sender)
    to_name = get_name(identifier=receiver)
    text = 'Dear %s: %s sent you %s' % (to_name, from_name, something)
    if group is not None:
        text += ' in group [%s]' % get_name(identifier=group)
    return text


def get_name(identifier: ID) -> str:
    doc = g_facebook.document(identifier=identifier)
    if doc is not None:
        name = doc.name
        if name is not None and len(name) > 0:
            return name
    name = identifier.name
    if name is not None and len(name) > 0:
        return name
    return str(identifier.address)


g_facebook = SharedFacebook()

# start as daemon
g_dispatcher = Dispatcher()
g_dispatcher.start()
