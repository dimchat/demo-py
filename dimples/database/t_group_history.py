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
from typing import Optional, Tuple, List

from aiou.mem import CachePool

from dimsdk import ID
from dimsdk import ReliableMessage
from dimsdk import GroupCommand, ResetCommand, ResignCommand

from ..utils import SharedCacheManager
from ..common import GroupHistoryDBI

from .dos import GroupHistoryStorage
from .redis import GroupHistoryCache

from .t_base import DbInfo, DbTask


class HisTask(DbTask):

    MEM_CACHE_EXPIRES = 300  # seconds
    MEM_CACHE_REFRESH = 32   # seconds

    def __init__(self, group: ID,
                 cache_pool: CachePool, redis: GroupHistoryCache, storage: GroupHistoryStorage,
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

    # Override
    async def _load_redis_cache(self) -> Optional[List[Tuple[GroupCommand, ReliableMessage]]]:
        # 1. the redis server will return None when cache not found
        # 2. when redis server return an empty array, no need to check local storage again
        return await self._redis.load_group_histories(group=self._group)

    # Override
    async def _save_redis_cache(self, value: List[Tuple[GroupCommand, ReliableMessage]]) -> bool:
        return await self._redis.save_group_histories(group=self._group, histories=value)

    # Override
    async def _load_local_storage(self) -> Optional[List[Tuple[GroupCommand, ReliableMessage]]]:
        # 1. the local storage will return an empty array, when no history in this group
        # 2. return empty array as a placeholder for the memory cache
        return await self._dos.load_group_histories(group=self._group)

    # Override
    async def _save_local_storage(self, value: List[Tuple[GroupCommand, ReliableMessage]]) -> bool:
        return await self._dos.save_group_histories(group=self._group, histories=value)


class GroupHistoryTable(GroupHistoryDBI):
    """ Implementations of GroupHistoryDBI """

    def __init__(self, info: DbInfo):
        super().__init__()
        man = SharedCacheManager()
        self._cache = man.get_pool(name='group.history')  # ID => List
        self._redis = GroupHistoryCache(connector=info.redis_connector)
        self._dos = GroupHistoryStorage(root=info.root_dir, public=info.public_dir, private=info.private_dir)
        self._lock = threading.Lock()

    def show_info(self):
        self._dos.show_info()

    def _new_task(self, group: ID) -> HisTask:
        return HisTask(group=group,
                       cache_pool=self._cache, redis=self._redis, storage=self._dos,
                       mutex_lock=self._lock)

    async def _load_group_histories(self, group: ID) -> List[Tuple[GroupCommand, ReliableMessage]]:
        task = self._new_task(group=group)
        histories = await task.load()
        if histories is None:
            histories = []
        return histories

    async def _save_group_histories(self, group: ID, histories: List[Tuple[GroupCommand, ReliableMessage]]) -> bool:
        task = self._new_task(group=group)
        return await task.save(value=histories)

    #
    #   Group History DBI
    #

    # Override
    async def save_group_history(self, group: ID, content: GroupCommand, message: ReliableMessage) -> bool:
        item = (content, message)
        histories = await self._load_group_histories(group=group)
        histories.append(item)
        return await self._save_group_histories(group=group, histories=histories)

    # Override
    async def get_group_histories(self, group: ID) -> List[Tuple[GroupCommand, ReliableMessage]]:
        return await self._load_group_histories(group=group)

    # Override
    async def get_reset_command_message(self, group: ID) -> Tuple[Optional[ResetCommand], Optional[ReliableMessage]]:
        histories = await self._load_group_histories(group=group)
        pos = len(histories)
        while pos > 0:
            pos -= 1
            his = histories[pos]
            cmd = his[0]
            msg = his[1]
            if isinstance(cmd, ResetCommand):
                return cmd, msg
        return None, None

    # Override
    async def clear_group_member_histories(self, group: ID) -> bool:
        histories = await self._load_group_histories(group=group)
        if len(histories) == 0:
            # history empty
            return True
        array = []
        removed = 0
        for his in histories:
            if isinstance(his[0], ResignCommand):
                # keep 'resign' command messages
                array.append(his)
            else:
                # remove other command messages
                removed += 1
        # if nothing changed, return True
        # else, save new histories
        return removed == 0 or await self._save_group_histories(group=group, histories=array)

    # Override
    async def clear_group_admin_histories(self, group: ID) -> bool:
        histories = await self._load_group_histories(group=group)
        if len(histories) == 0:
            # history empty
            return True
        array = []
        removed = 0
        for his in histories:
            if isinstance(his[0], ResignCommand):
                # remove 'resign' command messages
                removed += 1
            else:
                # keep other command messages
                array.append(his)
        # if nothing changed, return True
        # else, save new histories
        return removed == 0 or await self._save_group_histories(group=group, histories=array)
