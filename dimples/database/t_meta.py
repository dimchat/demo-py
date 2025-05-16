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

from aiou.mem import CachePool

from dimsdk import ID, Meta

from ..utils import Config
from ..utils import SharedCacheManager
from ..common import MetaDBI

from .dos import MetaStorage
from .redis import MetaCache

from .t_base import DbTask


class TaiTask(DbTask):

    MEM_CACHE_EXPIRES = 36000  # seconds
    MEM_CACHE_REFRESH = 32     # seconds

    def __init__(self, identifier: ID,
                 cache_pool: CachePool, redis: MetaCache, storage: MetaStorage,
                 mutex_lock: threading.Lock):
        super().__init__(cache_pool=cache_pool,
                         cache_expires=self.MEM_CACHE_EXPIRES,
                         cache_refresh=self.MEM_CACHE_REFRESH,
                         mutex_lock=mutex_lock)
        self._identifier = identifier
        self._redis = redis
        self._dos = storage

    # Override
    def cache_key(self) -> ID:
        return self._identifier

    # Override
    async def _load_redis_cache(self) -> Optional[Meta]:
        return await self._redis.get_meta(identifier=self._identifier)

    # Override
    async def _save_redis_cache(self, value: Meta) -> bool:
        return await self._redis.save_meta(meta=value, identifier=self._identifier)

    # Override
    async def _load_local_storage(self) -> Optional[Meta]:
        return await self._dos.get_meta(identifier=self._identifier)

    # Override
    async def _save_local_storage(self, value: Meta) -> bool:
        return await self._dos.save_meta(meta=value, identifier=self._identifier)


class MetaTable(MetaDBI):
    """ Implementations of MetaDBI """

    def __init__(self, config: Config):
        super().__init__()
        man = SharedCacheManager()
        self._cache = man.get_pool(name='meta')  # ID => Meta
        self._redis = MetaCache(config=config)
        self._dos = MetaStorage(config=config)
        self._lock = threading.Lock()

    def show_info(self):
        self._dos.show_info()

    def _new_task(self, identifier: ID) -> TaiTask:
        return TaiTask(identifier=identifier,
                       cache_pool=self._cache, redis=self._redis, storage=self._dos,
                       mutex_lock=self._lock)

    #
    #   Meta DBI
    #

    # Override
    async def get_meta(self, identifier: ID) -> Optional[Meta]:
        task = self._new_task(identifier=identifier)
        meta = await task.load()
        if meta is None:
            with self._lock:
                self._cache.update(key=identifier, value=None, life_span=300)
        return meta

    # Override
    async def save_meta(self, meta: Meta, identifier: ID) -> bool:
        # assert Meta.match_id(meta=meta, identifier=identifier), 'meta invalid: %s, %s' % (identifier, meta)
        task = self._new_task(identifier=identifier)
        return await task.save(value=meta)
