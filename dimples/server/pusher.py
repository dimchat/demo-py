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
from typing import Optional

from dimsdk import ID
from dimsdk import ContentType
from dimsdk import Envelope, ReliableMessage

from ..utils import Logging
from ..common import SharedFacebook

from .push_service import PushCenter


class Pusher(ABC):
    """ Notification Pusher """

    @abstractmethod
    def push_notification(self, msg: ReliableMessage):
        """ Push notification for msg receiver """
        raise NotImplemented


class DefaultPusher(Pusher, Logging):

    # Override
    def push_notification(self, msg: ReliableMessage):
        # 1. check original sender, group & msg type
        env = self._origin_envelope(msg=msg)
        receiver = msg.receiver
        sender = env.sender
        group = env.group
        msg_type = env.type
        # 2. build title & content text
        title, text = self._build_message(sender=sender, receiver=receiver, group=group, msg_type=msg_type)
        if text is None:
            # ignore msg type
            return
        # 3. check mute-list
        if self._is_mute(sender=sender, receiver=receiver, group=group):
            # muted by receiver
            return
        # push notification
        center = PushCenter()
        center.push_notification(sender=sender, receiver=receiver, title=title, content=text)

    # noinspection PyMethodMayBeStatic
    def _origin_envelope(self, msg: ReliableMessage) -> Envelope:
        """ get envelope of original message """
        origin = msg.get('origin')
        if origin is None:
            env = msg.envelope
        else:
            # forwarded message, separated by group assistant?
            env = Envelope.parse(envelope=origin)
            msg.pop('origin', None)
        return env

    # noinspection PyMethodMayBeStatic,PyUnusedLocal
    def _is_mute(self, sender: ID, receiver: ID, group: Optional[ID]) -> bool:
        """ check mute-list """
        # TODO: get mute command from receiver
        return False

    # noinspection PyMethodMayBeStatic
    def _build_message(self, sender: ID, receiver: ID, group: ID, msg_type: int) -> (str, str):
        """ build title, content for notification """
        return build_message(sender=sender, receiver=receiver, group=group, msg_type=msg_type)


def build_message(sender: ID, receiver: ID, group: ID, msg_type: int) -> (str, str):
    """ PNs: build text message for msg """
    if msg_type == 0:
        title = 'Message'
        something = 'a message'
    elif msg_type == ContentType.TEXT:
        title = 'Text Message'
        something = 'a text message'
    elif msg_type == ContentType.FILE:
        title = 'File'
        something = 'a file'
    elif msg_type == ContentType.IMAGE:
        title = 'Image'
        something = 'an image'
    elif msg_type == ContentType.AUDIO:
        title = 'Voice'
        something = 'a voice message'
    elif msg_type == ContentType.VIDEO:
        title = 'Video'
        something = 'a video'
    elif msg_type in [ContentType.MONEY, ContentType.TRANSFER]:
        title = 'Money'
        something = 'some money'
    else:
        # unknown type
        return None, None
    from_name = get_name(identifier=sender)
    to_name = get_name(identifier=receiver)
    text = 'Dear %s: %s sent you %s' % (to_name, from_name, something)
    if group is not None:
        text += ' in group [%s]' % get_name(identifier=group)
    return title, text


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
