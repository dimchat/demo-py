# -*- coding: utf-8 -*-
# ==============================================================================
# MIT License
#
# Copyright (c) 2021 Albert Moky
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
    Database module
    ~~~~~~~~~~~~~~~

"""

import time
from threading import Thread
from typing import TypeVar, Generic, Optional, Dict

from .singleton import Singleton


K = TypeVar('K')
V = TypeVar('V')


class CacheHolder(Generic[V]):

    def __init__(self, value: Optional[V] = None, life_span: float = 3600, now: float = None):
        super().__init__()
        self.__value = value
        if now is None:
            now = time.time()
        self.__expired = now + life_span

    @property
    def value(self) -> V:
        return self.__value

    def is_alive(self, now: float = None) -> bool:
        if now is None:
            now = time.time()
        return now < self.__expired

    def renewal(self, duration: float = 128, now: float = None):
        if now is None:
            now = time.time()
        self.__expired = now + duration


class CachePool(Generic[K, V]):

    def __init__(self):
        self.__holders: Dict[K, CacheHolder[V]] = {}  # key -> holder(value)

    def update(self, key: K, holder: CacheHolder = None,
               value: V = None, life_span: float = None, now: float = None):
        """ update: key -> holder(value) """
        if holder is None:
            holder = CacheHolder(value=value, life_span=life_span, now=now)
        self.__holders[key] = holder

    def fetch(self, key: K, now: float = None) -> (V, CacheHolder):
        """ fetch value & holder with key """
        holder = self.__holders.get(key)
        if holder is None:
            # holder not found
            return None, None
        elif holder.is_alive(now=now):
            return holder.value, holder
        else:
            # holder expired
            return None, holder

    def purge(self, now: float = None) -> int:
        """ remove all expired cache holders """
        count = 0
        keys = list(self.__holders.keys())
        for key in keys:
            holder = self.__holders.get(key)
            if holder is None or not holder.is_alive(now=now):
                # remove expired holders
                self.__holders.pop(key, None)
                count += 1
        return count


@Singleton
class CacheManager:

    def __init__(self):
        self.__pools: Dict[str, CachePool] = {}  # name -> pool
        # thread for cleaning caches
        self.__thread = None
        self.__running = False

    @property
    def running(self) -> bool:
        return self.__running

    def start(self):
        self.__force_stop()
        self.__running = True
        thread = Thread(target=self.run, daemon=True)
        self.__thread = thread
        thread.start()

    def __force_stop(self):
        self.__running = False
        thread: Thread = self.__thread
        if thread is not None:
            # waiting 2 seconds for stopping the thread
            self.__thread = None
            thread.join(timeout=5.0)

    def stop(self):
        self.__force_stop()

    def run(self):
        next_time = 0
        while self.running:
            # try to purge each 5 minutes
            now = time.time()
            if now < next_time:
                time.sleep(2)
                continue
            else:
                next_time = now + 300
            try:
                count = self.purge(now=now)
                print('[DB] purge %d item(s) from cache pools' % count)
            except Exception as error:
                print('[DB] failed to purge cache: %s' % error)
        print('[DB] stop %s' % self)

    def get_pool(self, name: str) -> CachePool[K, V]:
        """ get pool with name """
        pool = self.__pools.get(name)
        if pool is None:
            pool = CachePool()
            self.__pools[name] = pool
        return pool

    def purge(self, now: float) -> int:
        """ purge all pools """
        count = 0
        names = list(self.__pools.keys())
        for name in names:
            pool = self.__pools.get(name)
            if pool is not None:
                count += pool.purge(now=now)
        return count


class FrequencyChecker(Generic[K]):
    """ Frequency checker for duplicated queries """

    def __init__(self, expires: float = 3600):
        super().__init__()
        self.__expires = expires
        self.__map: Dict[K, float] = {}

    def expired(self, key: K, expires: float = None) -> bool:
        if expires is None:
            expires = self.__expires
        now = time.time()
        if now > self.__map.get(key, 0):
            self.__map[key] = now + expires
            return True
