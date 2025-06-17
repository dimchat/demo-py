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

from ..utils import Config
from ..common import UserDBI, ContactDBI

from .dos import UserStorage
from .redis import UserCache

from .t_base import DbTask, DataCache


class UsrTask(DbTask[ID, List[ID]]):

    def __init__(self, user: ID,
                 redis: UserCache, storage: UserStorage,
                 mutex_lock: threading.Lock, cache_pool: CachePool):
        super().__init__(mutex_lock=mutex_lock, cache_pool=cache_pool)
        self._user = user
        self._redis = redis
        self._dos = storage

    @property  # Override
    def cache_key(self) -> ID:
        return self._user

    # Override
    async def _read_data(self) -> Optional[List[ID]]:
        # 1. get from redis server
        contacts = await self._redis.get_contacts(identifier=self._user)
        if contacts is not None:
            return contacts
        # 2. get from local storage
        contacts = await self._dos.get_contacts(user=self._user)
        if contacts is not None:
            # 3. update redis server
            await self._redis.save_contacts(contacts=contacts, identifier=self._user)
            return contacts

    # Override
    async def _write_data(self, value: List[ID]) -> bool:
        # 1. store into redis server
        ok1 = await self._redis.save_contacts(contacts=value, identifier=self._user)
        # 2. save into local storage
        ok2 = await self._dos.save_contacts(contacts=value, user=self._user)
        return ok1 or ok2


class UserTable(DataCache, UserDBI, ContactDBI):
    """ Implementations of UserDBI """

    def __init__(self, config: Config):
        super().__init__(pool_name='contacts')  # ID => List[ID]
        self._redis = UserCache(config=config)
        self._dos = UserStorage(config=config)

    def show_info(self):
        self._dos.show_info()

    def _new_task(self, user: ID) -> UsrTask:
        return UsrTask(user=user,
                       redis=self._redis, storage=self._dos,
                       mutex_lock=self._mutex_lock, cache_pool=self._cache_pool)

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
