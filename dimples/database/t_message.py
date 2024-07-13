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

import threading
from typing import List

from dimsdk import DateTime
from dimsdk import ID
from dimsdk import ReliableMessage

from ..utils import SharedCacheManager
from ..common import ReliableMessageDBI

from .redis import MessageCache

from .t_base import DbInfo


class ReliableMessageTable(ReliableMessageDBI):
    """ Implementations of ReliableMessageDBI """

    MEM_CACHE_EXPIRES = 360  # seconds
    MEM_CACHE_REFRESH = 128  # seconds

    def __init__(self, info: DbInfo):
        super().__init__()
        man = SharedCacheManager()
        self.__cache = man.get_pool(name='reliable_messages')  # ID => List[ReliableMessages]
        self.__redis = MessageCache(connector=info.redis_connector)
        self.__lock = threading.Lock()

    # noinspection PyMethodMayBeStatic
    def show_info(self):
        print('!!! messages cached in memory only !!!')

    #
    #   Reliable Message DBI
    #

    # Override
    async def get_reliable_messages(self, receiver: ID, limit: int = 1024) -> List[ReliableMessage]:
        now = DateTime.now()
        cache_pool = self.__cache
        #
        #  1. check memory cache
        #
        value, holder = cache_pool.fetch(key=receiver, now=now)
        if value is not None:
            # got it from cache
            return value
        elif holder is None:
            # holder not exists, means it is the first querying
            pass
        elif holder.is_alive(now=now):
            # holder is not expired yet,
            # means the value is actually empty,
            # no need to check it again.
            return []
        #
        #  2. lock for querying
        #
        with self.__lock:
            # locked, check again to make sure the cache not exists.
            # (maybe the cache was updated by other threads while waiting the lock)
            value, holder = cache_pool.fetch(key=receiver, now=now)
            if value is not None:
                return value
            elif holder is None:
                pass
            elif holder.is_alive(now=now):
                return []
            else:
                # holder exists, renew the expired time for other threads
                holder.renewal(duration=self.MEM_CACHE_REFRESH, now=now)
            # 2.1. check redis server
            value = await self.__redis.get_reliable_messages(receiver=receiver, limit=limit)
            # 2.2. update memory cache
            self.__cache.update(key=receiver, value=value, life_span=self.MEM_CACHE_EXPIRES, now=now)
        #
        #  3. OK, return cached value
        #
        return value

    # Override
    async def cache_reliable_message(self, msg: ReliableMessage, receiver: ID) -> bool:
        with self.__lock:
            # 1. store into redis server
            if await self.__redis.save_reliable_message(msg=msg, receiver=receiver):
                # 2. clear cache to reload
                self.__cache.erase(key=receiver)
                return True

    # Override
    async def remove_reliable_message(self, msg: ReliableMessage, receiver: ID) -> bool:
        with self.__lock:
            # 1. remove from redis server
            if await self.__redis.remove_reliable_message(msg=msg, receiver=receiver):
                # 2. clear cache to reload
                self.__cache.erase(key=receiver)
                return True
