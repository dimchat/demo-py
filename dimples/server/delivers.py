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

from dimsdk import EntityType, ID
from dimsdk import ReliableMessage

from ..utils import Logging
from ..common import ReceiptCommand
from ..common import MessageDBI
from ..common import CommonFacebook

from .session_center import SessionCenter
from .pusher import Pusher
from .deliver import Deliver
from .dispatcher import Dispatcher


class BroadcastDeliver(Deliver, Logging):

    # Override
    def _get_recipients(self, receiver: ID) -> List[ID]:
        # get bot for search command
        if receiver in ['archivist@anywhere', 'archivists@everywhere']:
            self.info(msg='forward search command to archivist: %s -> %s' % receiver)
            # get from ANS
            bot = ID.parse(identifier='archivist')
            return [] if bot is None else [bot]
        # TODO: get neighbor stations
        return []

    # Override
    def _respond(self, msg: ReliableMessage, rcpt: List[ID]):
        text = 'Broadcast message delivering'
        cmd = ReceiptCommand.create(text=text, msg=msg)
        cmd['recipients'] = ID.revert(members=rcpt)
        return [cmd]

    # Override
    def _push_message(self, msg: ReliableMessage, receiver: ID) -> int:
        # node need to store broadcast message
        # push via active session directly
        return session_push(msg=msg, receiver=receiver)


class GroupDeliver(Deliver, Logging):

    def __init__(self, database: MessageDBI, facebook: CommonFacebook):
        super().__init__()
        self.__database = database
        self.__facebook = facebook

    @property
    def database(self) -> Optional[MessageDBI]:
        return self.__database

    @property
    def facebook(self) -> Optional[CommonFacebook]:
        return self.__facebook

    def _get_assistant(self, group: ID) -> Optional[ID]:
        facebook = self.facebook
        assistants = facebook.assistants(identifier=group)
        if assistants is None or len(assistants) == 0:
            # group assistant not found
            return None
        center = SessionCenter()
        for bot in assistants:
            if center.is_active(identifier=bot):
                # first online bot
                return bot
        # first bot
        return assistants[0]

    # Override
    def _get_recipients(self, receiver: ID) -> List[ID]:
        assert not receiver.is_broadcast, 'group ID error: %s' % receiver
        bot = self._get_assistant(group=receiver)
        if bot is None:
            # get from ANS
            bot = ID.parse(identifier='assistant')
        return [] if bot is None else [bot]

    # Override
    def _respond(self, msg: ReliableMessage, rcpt: List[ID]):
        text = 'Group message delivering'
        cmd = ReceiptCommand.create(text=text, msg=msg)
        cmd['assistants'] = ID.revert(members=rcpt)
        return [cmd]

    # Override
    def _push_message(self, msg: ReliableMessage, receiver: ID) -> int:
        # save message before push
        save_message(msg=msg, receiver=receiver, database=self.database)
        # push via active session
        return session_push(msg=msg, receiver=receiver)


class DefaultDeliver(Deliver, Logging):

    def __init__(self, database: MessageDBI, pusher: Pusher = None):
        super().__init__()
        self.__database = database
        self.__pusher = pusher

    @property
    def database(self) -> Optional[MessageDBI]:
        return self.__database

    @property
    def pusher(self) -> Optional[Pusher]:
        return self.__pusher

    # Override
    def _get_recipients(self, receiver: ID) -> List[ID]:
        assert not receiver.is_broadcast, 'receiver ID error: %s' % receiver
        assert not receiver.is_group, 'receiver ID error: %s' % receiver
        return [receiver]

    # Override
    def _respond(self, msg: ReliableMessage, rcpt: List[ID]):
        text = 'Message delivering'
        cmd = ReceiptCommand.create(text=text, msg=msg)
        # cmd['recipients'] = ID.revert(members=rcpt)
        return [cmd]

    # Override
    def _push_message(self, msg: ReliableMessage, receiver: ID) -> int:
        # save message before push
        save_message(msg=msg, receiver=receiver, database=self.database)
        # push via active session
        # 1. try to push via active session
        cnt = session_push(msg=msg, receiver=receiver)
        if cnt > 0:
            # receiver is login to current station, message pushed directly
            return cnt
        # 2. check for roaming and redirect
        if roamer_deliver(msg=msg, receiver=receiver):
            # receiver is roaming to other station, message redirected
            return 0
        # 3. user not roaming and not login, push notification
        if receiver.type == EntityType.USER:
            pusher = self.pusher
            if pusher is None:
                self.warning(msg='pusher not set yet, drop notification for: %s' % receiver)
            else:
                pusher.push_notification(msg=msg)
        return 0


def save_message(msg: ReliableMessage, receiver: ID, database: MessageDBI) -> bool:
    sender = msg.sender
    if sender.type == EntityType.STATION or receiver.type == EntityType.STATION:
        # no need to save station message
        return False
    assert receiver.is_user and not receiver.is_broadcast, 'receiver error: %s' % receiver
    return database.save_reliable_message(msg=msg, receiver=receiver)


def roamer_deliver(msg: ReliableMessage, receiver: ID) -> bool:
    """ deliver message via roamer """
    dispatcher = Dispatcher()
    roamer = dispatcher.roaming_deliver
    if roamer is not None:
        return roamer.roam_message(msg=msg, receiver=receiver)


def session_push(msg: ReliableMessage, receiver: ID) -> int:
    """ push message via active session(s) of receiver """
    cnt = 0
    center = SessionCenter()
    sessions = center.active_sessions(identifier=receiver)
    for sess in sessions:
        if sess.send_reliable_message(msg=msg):
            cnt += 1
    return cnt
