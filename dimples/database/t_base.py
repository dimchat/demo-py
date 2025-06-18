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

from ..utils import Logging
from ..utils import SharedCacheManager


class DataCache(Logging, Generic[K, V], ABC):

    def __init__(self, pool_name: str):
        super().__init__()
        man = SharedCacheManager()
        self._cache_pool = man.get_pool(name=pool_name)
        self._mutex_lock = threading.Lock()

    @property  # protected
    def cache(self) -> CachePool[K, V]:
        return self._cache_pool

    @property  # protected
    def lock(self) -> threading.Lock:
        return self._mutex_lock


class DbTask(Logging, Generic[K, V], ABC):

    MEM_CACHE_EXPIRES = 300  # seconds
    MEM_CACHE_REFRESH = 32   # seconds

    def __init__(self, mutex_lock: threading.Lock, cache_pool: CachePool,
                 cache_expires: float = None, cache_refresh: float = None):
        super().__init__()
        self._lock = mutex_lock
        # memory cache
        self._cache_pool = cache_pool
        # memory expires
        if cache_expires is None:
            self._cache_expires = self.MEM_CACHE_EXPIRES
        else:
            assert cache_expires > 0, 'cache expires durations error: %s' % cache_expires
            self._cache_expires = cache_expires
        # memory refresh
        if cache_refresh is None:
            self._cache_refresh = self.MEM_CACHE_REFRESH
        else:
            assert cache_refresh > 0, 'cache refresh durations error: %s' % cache_refresh
            self._cache_refresh = cache_refresh

    @property  # protected
    def lock(self) -> threading.Lock:
        return self._lock

    @property  # protected
    def cache_pool(self) -> CachePool[K, V]:
        return self._cache_pool

    @property  # protected
    def cache_expires(self) -> float:
        return self._cache_expires

    @property  # protected
    def cache_refresh(self) -> float:
        return self._cache_refresh

    @property  # protected
    @abstractmethod
    def cache_key(self) -> K:
        """ key for memory cache """
        raise NotImplemented

    @abstractmethod
    async def _read_data(self) -> Optional[V]:
        """ load value from local storage """
        raise NotImplemented

    @abstractmethod
    async def _write_data(self, value: V) -> bool:
        """ save value into local storage """
        raise NotImplemented

    async def save(self, value: V) -> bool:
        """ Task Save """
        with self.lock:
            # save into local storage
            ok = await self._write_data(value)
            if ok:
                # update memory cache
                self.cache_pool.update(key=self.cache_key, value=value, life_span=self.cache_expires)
            return ok

    async def load(self) -> Optional[V]:
        """ Task Load """
        now = time.time()
        key = self.cache_key
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
        with self.lock:
            # locked, check again to make sure the cache not exists.
            # (maybe the cache was updated by other threads while waiting the lock)
            value, holder = cache_pool.fetch(key=key, now=now)
            if value is not None:
                return value
            elif holder is None:
                # not load yet, wait to load
                pass
            elif holder.is_alive(now=now):
                # value not exists
                return None
            else:
                # holder exists, renew the expired time for other threads
                holder.renewal(duration=self.cache_refresh, now=now)
            # load from local storage
            value = await self._read_data()
            # update memory cache
            cache_pool.update(key=key, value=value, life_span=self.cache_expires, now=now)
        #
        #  3. OK, return cached value
        #
        return value
