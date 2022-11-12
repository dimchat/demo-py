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

import time
from typing import List

from dimsdk import EntityType, ID
from dimsdk import ReliableMessage

from ..utils import CacheHolder, CacheManager
from ..common import ReliableMessageDBI


class ReliableMessageTable(ReliableMessageDBI):
    """ Implementations of ReliableMessageDBI """

    # noinspection PyUnusedLocal
    def __init__(self, root: str = None, public: str = None, private: str = None):
        super().__init__()
        man = CacheManager()
        self.__msg_cache = man.get_pool(name='message')

    # noinspection PyMethodMayBeStatic
    def show_info(self):
        print('!!! messages cached in memory only !!!')

    #
    #   ReliableMessage DBI
    #

    # Override
    def reliable_messages(self, receiver: ID) -> List[ReliableMessage]:
        now = time.time()
        messages, _ = self.__msg_cache.fetch(key=receiver, now=now)
        return messages if messages is not None else []

    # Override
    def save_reliable_message(self, msg: ReliableMessage) -> bool:
        if is_ignored_message(msg=msg):
            return False
        now = time.time()
        receiver = msg.receiver
        # assert receiver.is_user, 'message receiver error: %s' % receiver
        messages, holder = self.__msg_cache.fetch(key=receiver, now=now)
        if messages is None:
            messages = [msg]
            self.__msg_cache.update(key=receiver, value=messages, life_span=3600*24*7, now=now)
        elif find_message(msg=msg, messages=messages) >= 0:
            # duplicated
            return False
        else:
            assert isinstance(holder, CacheHolder), 'msg cache error'
            # append to tail
            messages.append(msg)
            holder.update(value=messages, now=now)
        return True

    # Override
    def remove_reliable_message(self, msg: ReliableMessage) -> bool:
        now = time.time()
        receiver = msg.receiver
        # assert receiver.is_user, 'message receiver error: %s' % receiver
        messages, holder = self.__msg_cache.fetch(key=receiver, now=now)
        if messages is None:
            # not exists
            return False
        index = find_message(msg=msg, messages=messages)
        if index < 0:
            # not exists
            return False
        assert isinstance(holder, CacheHolder), 'msg cache error'
        assert isinstance(messages, list), 'msg list error: %s' % messages
        messages.pop(index)
        holder.update(value=messages, now=now)
        return True


def is_broadcast_message(msg: ReliableMessage):
    if msg.receiver.is_broadcast:
        return True
    group = msg.group
    return group is not None and group.is_broadcast


def is_ignored_message(msg: ReliableMessage) -> bool:
    if is_broadcast_message(msg=msg):
        # ignore broadcast message
        return True
    if msg.sender.type == EntityType.STATION:
        # ignore message from station
        return True
    if msg.receiver.type == EntityType.STATION:
        # ignore message to station
        return True


def find_message(msg: ReliableMessage, messages: List[ReliableMessage]) -> int:
    """ check message by signature """
    index = 0
    sig = msg.get('signature')
    for item in messages:
        if item.get('signature') == sig:
            return index
        index += 1
    # not found
    return -1
