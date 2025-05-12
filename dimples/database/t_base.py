# -*- coding: utf-8 -*-
# ==============================================================================
# MIT License
#
# Copyright (c) 2024 Albert Moky
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
import time
from abc import ABC, abstractmethod
from typing import Generic
from typing import Optional

from aiou.mem.cache import K, V
from aiou.mem import CachePool


class DbTask(Generic[K, V], ABC):

    def __init__(self, cache_pool: CachePool, cache_expires: float, cache_refresh: float, mutex_lock: threading.Lock):
        super().__init__()
        assert cache_expires > 0 and cache_refresh > 0, 'cache durations error: %s, %s' % (cache_expires, cache_refresh)
        # memory cache
        self.__cache_pool = cache_pool
        self.__cache_expires = cache_expires
        self.__cache_refresh = cache_refresh
        # lock
        self.__lock = mutex_lock

    @property  # protected
    def cache_pool(self) -> CachePool:
        return self.__cache_pool

    @property  # protected
    def cache_expires(self) -> float:
        return self.__cache_expires

    @property  # protected
    def cache_refresh(self) -> float:
        return self.__cache_refresh

    @abstractmethod
    def cache_key(self) -> K:
        """ key for memory cache """
        raise NotImplemented

    async def load(self) -> Optional[V]:
        now = time.time()
        key = self.cache_key()
        cache_pool = self.cache_pool
        #
        #  1. check memory cache
        #
        value, holder = cache_pool.fetch(key=key, now=now)
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
            return None
        #
        #  2. lock for querying
        #
        with self.__lock:
            # locked, check again to make sure the cache not exists.
            # (maybe the cache was updated by other threads while waiting the lock)
            value, holder = cache_pool.fetch(key=key, now=now)
            if value is not None:
                return value
            elif holder is None:
                pass
            elif holder.is_alive(now=now):
                return None
            else:
                # holder exists, renew the expired time for other threads
                holder.renewal(duration=self.cache_refresh, now=now)
            # 2.1. check redis server
            value = await self._load_redis_cache()
            if value is None:
                # 2.2. check local storage
                value = await self._load_local_storage()
                if value is not None:
                    # 2.3. update redis server
                    await self._save_redis_cache(value=value)
            # update memory cache
            cache_pool.update(key=key, value=value, life_span=self.cache_expires, now=now)
        #
        #  3. OK, return cached value
        #
        return value

    async def save(self, value: V) -> bool:
        now = time.time()
        key = self.cache_key()
        cache_pool = self.cache_pool
        with self.__lock:
            # store into memory cache
            cache_pool.update(key=key, value=value, life_span=self.cache_expires, now=now)
            # store into redis server
            ok1 = await self._save_redis_cache(value=value)
            # save into local storage
            ok2 = await self._save_local_storage(value=value)
        # OK
        return ok1 or ok2

    @abstractmethod
    async def _load_redis_cache(self) -> Optional[V]:
        """ get value from redis server """
        raise NotImplemented

    @abstractmethod
    async def _save_redis_cache(self, value: V) -> bool:
        """ save value into redis server """
        raise NotImplemented

    @abstractmethod
    async def _load_local_storage(self) -> Optional[V]:
        """ get value from local storage """
        raise NotImplemented

    @abstractmethod
    async def _save_local_storage(self, value: V) -> bool:
        """ save value into local storage """
        raise NotImplemented
