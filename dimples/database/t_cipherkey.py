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
from typing import Optional

from dimsdk import DateTime
from dimsdk import ID, SymmetricKey
from dimplugins import PlainKey

from ..utils import SharedCacheManager
from ..common import CipherKeyDBI

from .t_base import DbInfo


class CipherKeyTable(CipherKeyDBI):
    """ Implementations of CipherKeyDBI """

    CACHE_EXPIRES = 3600*24*7  # seconds

    # noinspection PyUnusedLocal
    def __init__(self, info: DbInfo):
        super().__init__()
        man = SharedCacheManager()
        self._cache = man.get_pool(name='cipher_keys')  # (ID, ID) => SymmetricKey
        self._lock = threading.Lock()

    # noinspection PyMethodMayBeStatic
    def show_info(self):
        print('!!!      cipher key in memory only !!!')

    #
    #   Cipher Key DBI
    #

    # Override
    async def get_cipher_key(self, sender: ID, receiver: ID, generate: bool = False) -> Optional[SymmetricKey]:
        if receiver.is_broadcast:
            return PlainKey()
        now = DateTime.now()
        direction = (sender, receiver)
        cache_pool = self._cache
        #
        #  1. check memory cache
        #
        pwd, _ = cache_pool.fetch(key=direction, now=now)
        if pwd is not None:
            # got it from cache
            return pwd
        #
        #  2. lock for querying
        #
        with self._lock:
            # locked, check again to make sure the cache not exists.
            # (maybe the cache was updated by other threads while waiting the lock)
            pwd, _ = cache_pool.fetch(key=direction, now=now)
            if pwd is None and generate:
                # generate and cache it
                pwd = SymmetricKey.generate(algorithm=SymmetricKey.AES)
                assert pwd is not None, 'failed to generate symmetric key'
                cache_pool.update(key=direction, value=pwd, life_span=self.CACHE_EXPIRES, now=now)
        #
        #  3. OK, return cached value
        #
        return pwd

    # Override
    async def cache_cipher_key(self, key: SymmetricKey, sender: ID, receiver: ID):
        if receiver.is_broadcast:
            # no need to store cipher key for broadcast message
            return False
        now = DateTime.now()
        direction = (sender, receiver)
        cache_pool = self._cache
        with self._lock:
            # store into memory cache
            cache_pool.update(key=direction, value=key, life_span=self.CACHE_EXPIRES, now=now)
        return True
