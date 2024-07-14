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
from typing import List, Optional

from aiou.mem import CachePool

from dimsdk import ID

from ..utils import SharedCacheManager
from ..common import UserDBI, ContactDBI

from .dos import UserStorage
from .redis import UserCache

from .t_base import DbInfo, DbTask


class UsrTask(DbTask):

    MEM_CACHE_EXPIRES = 300  # seconds
    MEM_CACHE_REFRESH = 32   # seconds

    def __init__(self, user: ID,
                 cache_pool: CachePool, redis: UserCache, storage: UserStorage,
                 mutex_lock: threading.Lock):
        super().__init__(cache_pool=cache_pool,
                         cache_expires=self.MEM_CACHE_EXPIRES,
                         cache_refresh=self.MEM_CACHE_REFRESH,
                         mutex_lock=mutex_lock)
        self._user = user
        self._redis = redis
        self._dos = storage

    # Override
    def cache_key(self) -> ID:
        return self._user

    # Override
    async def _load_redis_cache(self) -> Optional[List[ID]]:
        return await self._redis.get_contacts(identifier=self._user)

    # Override
    async def _save_redis_cache(self, value: List[ID]) -> bool:
        return await self._redis.save_contacts(contacts=value, identifier=self._user)

    # Override
    async def _load_local_storage(self) -> Optional[List[ID]]:
        return await self._dos.get_contacts(user=self._user)

    # Override
    async def _save_local_storage(self, value: List[ID]) -> bool:
        return await self._dos.save_contacts(contacts=value, user=self._user)


class UserTable(UserDBI, ContactDBI):
    """ Implementations of UserDBI """

    def __init__(self, info: DbInfo):
        super().__init__()
        man = SharedCacheManager()
        self._cache = man.get_pool(name='contacts')  # ID => List[ID]
        self._redis = UserCache(connector=info.redis_connector)
        self._dos = UserStorage(root=info.root_dir, public=info.public_dir, private=info.private_dir)
        self._lock = threading.Lock()

    def show_info(self):
        self._dos.show_info()

    def _new_task(self, user: ID) -> UsrTask:
        return UsrTask(user=user,
                       cache_pool=self._cache, redis=self._redis, storage=self._dos,
                       mutex_lock=self._lock)

    #
    #   User DBI
    #

    # Override
    async def get_local_users(self) -> List[ID]:
        return []

    # Override
    async def save_local_users(self, users: List[ID]) -> bool:
        pass

    #
    #   Contact DBI
    #

    # Override
    async def get_contacts(self, user: ID) -> List[ID]:
        task = self._new_task(user=user)
        contacts = await task.load()
        return [] if contacts is None else contacts

    # Override
    async def save_contacts(self, contacts: List[ID], user: ID) -> bool:
        task = self._new_task(user=user)
        return await task.save(value=contacts)
