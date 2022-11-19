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
from typing import List

from dimsdk import ID
from dimsdk import ReliableMessage

from ..utils import Logging
from ..common import MessageDBI
from ..common import CommonFacebook

from .session_center import SessionCenter
from .pusher import Pusher


class Deliver(ABC):

    @abstractmethod
    def deliver_message(self, msg: ReliableMessage) -> int:
        raise NotImplemented


class BroadcastDeliver(Deliver, Logging):

    def __init__(self, facebook: CommonFacebook):
        super().__init__()
        self.__facebook = facebook

    @property
    def facebook(self) -> CommonFacebook:
        return self.__facebook

    @classmethod
    def get_sent_nodes(cls, msg: ReliableMessage) -> List[ID]:
        sent_nodes = msg.get('sent_nodes')
        if sent_nodes is None:
            return []
        return ID.convert(members=sent_nodes)

    @classmethod
    def set_sent_nodes(cls, msg: ReliableMessage, sent_nodes: List[ID]):
        if sent_nodes is None or len(sent_nodes) == 0:
            msg.pop('sent_nodes', None)
        else:
            msg['sent_nodes'] = ID.revert(members=sent_nodes)

    # noinspection PyMethodMayBeStatic,PyUnusedLocal
    def _get_neighbor_stations(self, receiver: ID) -> List[ID]:
        # TODO: get neighbor stations
        return []

    # noinspection PyMethodMayBeStatic
    def _get_current_station(self) -> ID:
        facebook = self.facebook
        current = facebook.current_user
        return current.identifier

    # Override
    def deliver_message(self, msg: ReliableMessage) -> int:
        receiver = msg.receiver
        assert receiver.is_broadcast, 'broadcast ID error: %s' % receiver
        total = 0
        sent_nodes = self.get_sent_nodes(msg=msg)
        neighbors = self._get_neighbor_stations(receiver=receiver)
        current = self._get_current_station()
        # 1. broadcast to neighbor stations
        self.info(msg='broadcasting message (%s) for: %s, current: %s, neighbors: %s'
                      % (get_sig(msg=msg), receiver, current, neighbors))
        for octopus in neighbors:
            assert octopus != current, 'neighbour station error: %s => %s' % (current, neighbors)
            if octopus in sent_nodes:
                self.info(msg='neighbour station (%s) already sent' % octopus)
                continue
            cnt = session_push(msg=msg, receiver=octopus)
            if cnt > 0:
                self.info(msg='message (%s) push to %s, %d session(s)' % (get_sig(msg=msg), octopus, cnt))
                sent_nodes.append(octopus)
                total += cnt
        # 2. send to other neighbor(s) via my octopus
        self.set_sent_nodes(msg=msg, sent_nodes=sent_nodes)
        assert current is not None, 'current station not found'
        cnt = session_push(msg=msg, receiver=current)
        if cnt > 0:
            self.info(msg='message (%s) push to %s, %d session(s)' % (get_sig(msg=msg), current, cnt))
            total += cnt
        return total


class GroupDeliver(Deliver, Logging):

    def __init__(self, database: MessageDBI, facebook: CommonFacebook):
        super().__init__()
        self.__database = database
        self.__facebook = facebook

    @property
    def database(self) -> MessageDBI:
        return self.__database

    @property
    def facebook(self) -> CommonFacebook:
        return self.__facebook

    # noinspection PyMethodMayBeStatic
    def _get_assistants(self, group: ID) -> List[ID]:
        facebook = self.facebook
        assistants = facebook.assistants(identifier=group)
        if assistants is None:
            # get from ANS
            bot = ID.parse(identifier='assistant')
            if bot is None:
                assistants = []
            else:
                assistants = [bot]
        return assistants

    def _save_group_message(self, msg: ReliableMessage, group: ID, assistants: List[ID]) -> int:
        db = self.database
        if db is None:
            self.warning(msg='message db not set, drop message for: %s, %s' % (group, assistants))
            return -1
        if len(assistants) > 0:
            # change group receiver to first bot
            bot = assistants[0]  # TODO: or let bot = 'assistant@anywhere'?
            msg['group'] = str(group)
            msg['receiver'] = str(bot)
            # save the message for first bot
            db.save_reliable_message(msg=msg)
            return 0
        else:
            self.warning(msg='assistants not set, drop message for: %s' % group)
            return -2

    # Override
    def deliver_message(self, msg: ReliableMessage) -> int:
        receiver = msg.receiver
        assert receiver.is_group, 'group ID error: %s' % receiver
        cnt = 0
        # 1. redirect to group assistant
        assistants = self._get_assistants(group=receiver)
        self.info(msg='redirecting group message (%s) for: %s, assistants: %s'
                      % (get_sig(msg=msg), receiver, assistants))
        for bot in assistants:
            cnt += session_push(msg=msg, receiver=bot)
            if cnt > 0:
                # got one group assistant online,
                # no need to push to other assistant(s).
                self.info(msg='message (%s) push to %s, %d session(s)' % (get_sig(msg=msg), bot, cnt))
                break
        # 2. if no assistant online, store it
        if cnt == 0:
            self._save_group_message(msg=msg, group=receiver, assistants=assistants)
        return cnt


class DefaultDeliver(Deliver, Logging):

    def __init__(self, database: MessageDBI, pusher: Pusher):
        super().__init__()
        self.__database = database
        self.__pusher = pusher

    @property
    def database(self) -> MessageDBI:
        return self.__database

    @property
    def pusher(self) -> Pusher:
        return self.__pusher

    def _save_message(self, msg: ReliableMessage, receiver: ID) -> int:
        db = self.database
        if db is None:
            self.warning(msg='message db not set, drop message for: %s' % receiver)
            return -1
        db.save_reliable_message(msg=msg)
        return 0

    # Override
    def deliver_message(self, msg: ReliableMessage) -> int:
        receiver = msg.receiver
        assert receiver.is_user, 'receiver ID error: %s' % receiver
        # 1. push message to the waiting queue in the receiver's session(s)
        cnt = session_push(msg=msg, receiver=receiver)
        if cnt > 0:
            # success
            self.info(msg='message (%s) pushed to %s, %d session(s)' % (get_sig(msg=msg), receiver, cnt))
            return cnt
        # 2. no session active, store the message
        if self._save_message(msg=msg, receiver=receiver) < 0:
            # db error
            return -1
        # 3. try to push notification
        delegate = self.pusher
        if delegate is None:
            self.warning(msg='pusher not set yet, drop notification for: %s' % receiver)
        else:
            delegate.push_notification(msg=msg)
        return 0


def session_push(msg: ReliableMessage, receiver: ID) -> int:
    cnt = 0
    center = SessionCenter()
    sessions = center.active_sessions(identifier=receiver)
    for sess in sessions:
        if sess.send_reliable_message(msg=msg):
            cnt += 1
    return cnt


def get_sig(msg: ReliableMessage) -> str:
    sig = msg.get('signature')
    return sig[-8:]  # last 6 bytes (signature in base64)
