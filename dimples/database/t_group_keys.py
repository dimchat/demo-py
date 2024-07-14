# -*- coding: utf-8 -*-
# ==============================================================================
# MIT License
#
# Copyright (c) 2023 Albert Moky
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
from typing import Optional, Tuple, Dict

from aiou.mem import CachePool

from dimsdk import ID

from ..utils import SharedCacheManager
from ..common import GroupKeysDBI

from .dos import GroupKeysStorage
from .redis import GroupKeysCache

from .t_base import DbInfo, DbTask


class PwdTask(DbTask):

    MEM_CACHE_EXPIRES = 300  # seconds
    MEM_CACHE_REFRESH = 32   # seconds

    def __init__(self, group: ID, sender: ID,
                 cache_pool: CachePool, redis: GroupKeysCache, storage: GroupKeysStorage,
                 mutex_lock: threading.Lock):
        super().__init__(cache_pool=cache_pool,
                         cache_expires=self.MEM_CACHE_EXPIRES,
                         cache_refresh=self.MEM_CACHE_REFRESH,
                         mutex_lock=mutex_lock)
        self._group = group
        self._sender = sender
        self._redis = redis
        self._dos = storage

    # Override
    def cache_key(self) -> Tuple[ID, ID]:
        return self._group, self._sender

    # Override
    async def _load_redis_cache(self) -> Optional[Dict[str, str]]:
        return await self._redis.get_group_keys(group=self._group, sender=self._sender)

    # Override
    async def _save_redis_cache(self, value: Dict[str, str]) -> bool:
        return await self._redis.save_group_keys(group=self._group, sender=self._sender, keys=value)

    # Override
    async def _load_local_storage(self) -> Optional[Dict[str, str]]:
        return await self._dos.get_group_keys(group=self._group, sender=self._sender)

    # Override
    async def _save_local_storage(self, value: Dict[str, str]) -> bool:
        return await self._dos.save_group_keys(group=self._group, sender=self._sender, keys=value)


class GroupKeysTable(GroupKeysDBI):
    """ Implementations of GroupKeysDBI """

    def __init__(self, info: DbInfo):
        super().__init__()
        man = SharedCacheManager()
        self._cache = man.get_pool(name='group.keys')  # (ID, ID) => Dict
        self._redis = GroupKeysCache(connector=info.redis_connector)
        self._dos = GroupKeysStorage(root=info.root_dir, public=info.public_dir, private=info.private_dir)
        self._lock = threading.Lock()

    def show_info(self):
        self._dos.show_info()

    def _new_task(self, group: ID, sender: ID) -> PwdTask:
        return PwdTask(group=group, sender=sender,
                       cache_pool=self._cache, redis=self._redis, storage=self._dos,
                       mutex_lock=self._lock)

    async def _merge_keys(self, group: ID, sender: ID, keys: Dict[str, str]) -> Dict[str, str]:
        if 'digest' not in keys:
            # FIXME: old version?
            return keys
        # 0. check old record
        table = await self.get_group_keys(group=group, sender=sender)
        if table is None or 'digest' not in table:
            # new keys
            return keys
        elif table.get('digest') != keys.get('digest'):
            # key changed
            return keys
        else:
            # same digest, merge keys
            table = table.copy()
            for receiver in keys:
                table[receiver] = keys[receiver]
            return table

    async def load_group_keys(self, group: ID, sender: ID) -> Dict[str, str]:
        task = self._new_task(group=group, sender=sender)
        keys = await task.load()
        if keys is None:
            keys = {}  # placeholder
            with self._lock:
                await self._redis.save_group_keys(group=group, sender=sender, keys=keys)
                self._cache.update(key=(group, sender), value=keys, life_span=PwdTask.MEM_CACHE_EXPIRES)
        return keys

    #
    #   Group Keys DBI
    #

    # Override
    async def save_group_keys(self, group: ID, sender: ID, keys: Dict[str, str]) -> bool:
        task = self._new_task(group=group, sender=sender)
        return await task.save(value=keys)

    # Override
    async def get_group_keys(self, group: ID, sender: ID) -> Optional[Dict[str, str]]:
        return await self.load_group_keys(group=group, sender=sender)
