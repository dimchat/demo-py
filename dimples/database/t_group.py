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
from abc import ABC
from typing import Optional, List

from aiou.mem import CachePool

from dimsdk import ID

from ..utils import Config
from ..utils import SharedCacheManager
from ..common import GroupDBI

from .dos import GroupStorage
from .redis import GroupCache

from .t_base import DbTask


# noinspection PyAbstractClass
class GrpTask(DbTask, ABC):

    MEM_CACHE_EXPIRES = 300  # seconds
    MEM_CACHE_REFRESH = 32   # seconds

    def __init__(self, group: ID,
                 cache_pool: CachePool, redis: GroupCache, storage: GroupStorage,
                 mutex_lock: threading.Lock):
        super().__init__(cache_pool=cache_pool,
                         cache_expires=self.MEM_CACHE_EXPIRES,
                         cache_refresh=self.MEM_CACHE_REFRESH,
                         mutex_lock=mutex_lock)
        self._group = group
        self._redis = redis
        self._dos = storage

    # Override
    def cache_key(self) -> ID:
        return self._group


class MemberTask(GrpTask):

    # Override
    async def _load_redis_cache(self) -> Optional[List[ID]]:
        # 1. the redis server will return None when cache not found
        # 2. when redis server return an empty array, no need to check local storage again
        return await self._redis.get_members(group=self._group)

    # Override
    async def _save_redis_cache(self, value: List[ID]) -> bool:
        return await self._redis.save_members(members=value, group=self._group)

    # Override
    async def _load_local_storage(self) -> Optional[List[ID]]:
        # 1. the local storage will return an empty array, when no member in this group
        # 2. return empty array as a placeholder for the memory cache
        return await self._dos.get_members(group=self._group)

    # Override
    async def _save_local_storage(self, value: List[ID]) -> bool:
        return await self._dos.save_members(members=value, group=self._group)


class BotTask(GrpTask):

    # Override
    async def _load_redis_cache(self) -> Optional[List[ID]]:
        # 1. the redis server will return None when cache not found
        # 2. when redis server return an empty array, no need to check local storage again
        return await self._redis.get_assistants(group=self._group)

    # Override
    async def _save_redis_cache(self, value: List[ID]) -> bool:
        return await self._redis.save_assistants(assistants=value, group=self._group)

    # Override
    async def _load_local_storage(self) -> Optional[List[ID]]:
        # 1. the local storage will return an empty array, when no bot for this group
        # 2. return empty array as a placeholder for the memory cache
        return await self._dos.get_assistants(group=self._group)

    # Override
    async def _save_local_storage(self, value: List[ID]) -> bool:
        return await self._dos.save_assistants(assistants=value, group=self._group)


class AdminTask(GrpTask):

    # Override
    async def _load_redis_cache(self) -> Optional[List[ID]]:
        # 1. the redis server will return None when cache not found
        # 2. when redis server return an empty array, no need to check local storage again
        return await self._redis.get_administrators(group=self._group)

    # Override
    async def _save_redis_cache(self, value: List[ID]) -> bool:
        return await self._redis.save_administrators(administrators=value, group=self._group)

    # Override
    async def _load_local_storage(self) -> Optional[List[ID]]:
        # 1. the local storage will return an empty array, when no admin in this group
        # 2. return empty array as a placeholder for the memory cache
        return await self._dos.get_administrators(group=self._group)

    # Override
    async def _save_local_storage(self, value: List[ID]) -> bool:
        return await self._dos.save_administrators(administrators=value, group=self._group)


class GroupTable(GroupDBI):
    """ Implementations of GroupDBI """

    def __init__(self, config: Config):
        super().__init__()
        man = SharedCacheManager()
        self._member_cache = man.get_pool(name='group.members')        # ID => List[ID]
        self._bot_cache = man.get_pool(name='group.assistants')        # ID => List[ID]
        self._admin_cache = man.get_pool(name='group.administrators')  # ID => List[ID]
        self._redis = GroupCache(config=config)
        self._dos = GroupStorage(config=config)
        self._lock = threading.Lock()

    def show_info(self):
        self._dos.show_info()

    def _new_member_task(self, group: ID) -> GrpTask:
        return MemberTask(group=group,
                          cache_pool=self._member_cache, redis=self._redis, storage=self._dos,
                          mutex_lock=self._lock)

    def _new_bot_task(self, group: ID) -> GrpTask:
        return BotTask(group=group,
                       cache_pool=self._bot_cache, redis=self._redis, storage=self._dos,
                       mutex_lock=self._lock)

    def _new_admin_task(self, group: ID) -> GrpTask:
        return AdminTask(group=group,
                         cache_pool=self._admin_cache, redis=self._redis, storage=self._dos,
                         mutex_lock=self._lock)

    #
    #   Group DBI
    #

    # Override
    async def get_founder(self, group: ID) -> Optional[ID]:
        pass

    # Override
    async def get_owner(self, group: ID) -> Optional[ID]:
        pass

    # Override
    async def get_members(self, group: ID) -> List[ID]:
        task = self._new_member_task(group=group)
        members = await task.load()
        return [] if members is None else members

    # Override
    async def save_members(self, members: List[ID], group: ID) -> bool:
        task = self._new_member_task(group=group)
        return await task.save(value=members)

    # Override
    async def get_assistants(self, group: ID) -> List[ID]:
        task = self._new_bot_task(group=group)
        bots = await task.load()
        return [] if bots is None else bots

    # Override
    async def save_assistants(self, assistants: List[ID], group: ID) -> bool:
        task = self._new_bot_task(group=group)
        return await task.save(value=assistants)

    # Override
    async def get_administrators(self, group: ID) -> List[ID]:
        task = self._new_admin_task(group=group)
        admins = await task.load()
        return [] if admins is None else admins

    # Override
    async def save_administrators(self, administrators: List[ID], group: ID) -> bool:
        task = self._new_admin_task(group=group)
        return await task.save(value=administrators)
