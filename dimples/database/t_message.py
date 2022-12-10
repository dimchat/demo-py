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
from typing import List, Tuple

from dimsdk import ID
from dimsdk import ReliableMessage

from ..utils import CacheHolder, CacheManager
from ..common import ReliableMessageDBI


class ReliableMessageTable(ReliableMessageDBI):
    """ Implementations of ReliableMessageDBI """

    CACHE_LIMIT = 71680  # only cache last messages

    # noinspection PyUnusedLocal
    def __init__(self, root: str = None, public: str = None, private: str = None):
        super().__init__()
        man = CacheManager()
        self.__msg_cache = man.get_pool(name='message')  # ID => List[ReliableMessage]

    # noinspection PyMethodMayBeStatic
    def show_info(self):
        print('!!! messages cached in memory only !!!')

    #
    #   ReliableMessage DBI
    #

    # Override
    def reliable_messages(self, receiver: ID, start: int = 0, limit: int = 1024) -> Tuple[List[ReliableMessage], int]:
        now = time.time()
        # get all messages
        messages, _ = self.__msg_cache.fetch(key=receiver, now=now)
        if messages is None:
            messages = []
            total = 0
        else:
            total = len(messages)
        # check range: [start, end)
        start, end = get_range(start=start, limit=limit, total=total)
        if 0 < start or end < total:
            messages = messages[start:end]
        # return message list and remaining count
        return messages, total - end

    # Override
    def save_reliable_message(self, msg: ReliableMessage, receiver: ID) -> bool:
        now = time.time()
        # assert receiver.is_user, 'message receiver error: %s' % receiver
        messages, holder = self.__msg_cache.fetch(key=receiver, now=now)
        if messages is None:
            messages = [msg]
            self.__msg_cache.update(key=receiver, value=messages, life_span=3600*24*7, now=now)
        elif find_message(msg=msg, messages=messages) >= 0:
            # duplicated
            return False
        else:
            assert isinstance(holder, CacheHolder), 'msg cache holder error: %s' % holder
            assert isinstance(messages, list), 'msg cache list error: %s' % messages
            while len(messages) > self.CACHE_LIMIT:
                # overflow
                messages.pop(0)
            # append to tail
            messages.append(msg)
            holder.update(value=messages, now=now)
        return True

    # Override
    def remove_reliable_message(self, msg: ReliableMessage, receiver: ID) -> bool:
        now = time.time()
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


def get_range(start: int, limit: int, total: int) -> Tuple[int, int]:
    assert limit > 0, 'limit error: %d' % limit
    assert total >= 0, 'total count error: %d' % total
    # seek for start
    if start < 0:
        # seek from the tail
        start += total
        if start < 0:
            # too few data, start from the head
            start = 0
    elif start > total:
        # out of range
        return 0, 0
        # start = total
    # seek for end
    end = start + limit
    if end > total:
        # too few data, stop at the tail
        end = total
    return start, end
