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
class GrpTask(DbTask[ID, List[ID]], ABC):

    def __init__(self, group: ID,
                 redis: GroupCache, storage: GroupStorage,
                 mutex_lock: threading.Lock, cache_pool: CachePool):
        super().__init__(mutex_lock=mutex_lock, cache_pool=cache_pool)
        self._group = group
        self._redis = redis
        self._dos = storage

    @property  # Override
    def cache_key(self) -> ID:
        return self._group


class MemberTask(GrpTask):

    # Override
    async def _read_data(self) -> Optional[List[ID]]:
        # 1. the redis server will return None when cache not found
        # 2. when redis server return an empty array, no need to check local storage again
        members = await self._redis.get_members(group=self._group)
        if members is not None:
            return members
        # 3. the local storage will return an empty array, when no member in this group
        members = await self._dos.get_members(group=self._group)
        if members is None:
            # 4. return empty array as a placeholder for the memory cache
            members = []
        # 5. update redis server
        await self._dos.save_members(members=members, group=self._group)
        return members

    # Override
    async def _write_data(self, value: List[ID]) -> bool:
        # 1. store into redis server
        ok1 = await self._redis.save_members(members=value, group=self._group)
        # 2. save into local storage
        ok2 = await self._dos.save_members(members=value, group=self._group)
        return ok1 or ok2


class BotTask(GrpTask):

    # Override
    async def _read_data(self) -> Optional[List[ID]]:
        # 1. the redis server will return None when cache not found
        # 2. when redis server return an empty array, no need to check local storage again
        bots = await self._redis.get_assistants(group=self._group)
        if bots is not None:
            return bots
        # 3. the local storage will return an empty array, when no bot for this group
        bots = await self._dos.get_assistants(group=self._group)
        if bots is None:
            # 4. return empty array as a placeholder for the memory cache
            bots = []
        # 5. update redis server
        await self._dos.save_assistants(assistants=bots, group=self._group)
        return bots

    # Override
    async def _write_data(self, value: List[ID]) -> bool:
        # 1. store into redis server
        ok1 = await self._redis.save_assistants(assistants=value, group=self._group)
        # 2. save into local storage
        ok2 = await self._dos.save_assistants(assistants=value, group=self._group)
        return ok1 or ok2


class AdminTask(GrpTask):

    # Override
    async def _read_data(self) -> Optional[List[ID]]:
        # 1. the redis server will return None when cache not found
        # 2. when redis server return an empty array, no need to check local storage again
        admins = await self._redis.get_administrators(group=self._group)
        if admins is not None:
            return admins
        # 3. the local storage will return an empty array, when no admin in this group
        admins = await self._dos.get_administrators(group=self._group)
        if admins is None:
            # 4. return empty array as a placeholder for the memory cache
            admins = []
        # 5. update redis server
        await self._dos.save_administrators(administrators=admins, group=self._group)
        return admins

    # Override
    async def _write_data(self, value: List[ID]) -> bool:
        # 1. store into redis server
        ok1 = await self._redis.save_administrators(administrators=value, group=self._group)
        # 2. save into local storage
        ok2 = await self._dos.save_administrators(administrators=value, group=self._group)
        return ok1 or ok2


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
                          redis=self._redis, storage=self._dos,
                          mutex_lock=self._lock, cache_pool=self._member_cache)

    def _new_bot_task(self, group: ID) -> GrpTask:
        return BotTask(group=group,
                       redis=self._redis, storage=self._dos,
                       mutex_lock=self._lock, cache_pool=self._bot_cache)

    def _new_admin_task(self, group: ID) -> GrpTask:
        return AdminTask(group=group,
                         redis=self._redis, storage=self._dos,
                         mutex_lock=self._lock, cache_pool=self._admin_cache)

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
