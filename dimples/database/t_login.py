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
from typing import Optional, Tuple

from aiou.mem import CachePool

from dimsdk import ID
from dimsdk import ReliableMessage

from ..utils import Config
from ..utils import is_before
from ..common import LoginDBI, LoginCommand

from .dos import LoginStorage
from .redis import LoginCache

from .t_base import DbTask, DataCache


class CmdTask(DbTask[ID, Tuple[Optional[LoginCommand], Optional[ReliableMessage]]]):

    def __init__(self, user: ID,
                 redis: LoginCache, storage: LoginStorage,
                 mutex_lock: threading.Lock, cache_pool: CachePool):
        super().__init__(mutex_lock=mutex_lock, cache_pool=cache_pool)
        self._user = user
        self._redis = redis
        self._dos = storage

    @property  # Override
    def cache_key(self) -> ID:
        return self._user

    # Override
    async def _read_data(self) -> Optional[Tuple[Optional[LoginCommand], Optional[ReliableMessage]]]:
        # 1. the redis server will return None when cache not found
        # 2. when redis server return a tuple with None values, no need to check local storage again
        pair = await self._redis.load_login(user=self._user)
        if pair is not None:
            return pair
        # 3. the local storage will return a tuple with None values, when command not found
        pair = await self._dos.get_login_command_message(user=self._user)
        if pair is None:
            # 4. return a tuple with None values as a placeholder for the memory cache
            cmd = None
            msg = None
            pair = [cmd, msg]
        else:
            assert len(pair) == 2, 'login command message error: %s -> %s' % (self._user, pair)
            cmd = pair[0]
            msg = pair[1]
        # 5. update redis server
        await self._redis.save_login(user=self._user, content=cmd, msg=msg)
        return pair

    # Override
    async def _write_data(self, value: Tuple[Optional[LoginCommand], Optional[ReliableMessage]]) -> bool:
        cmd = value[0]
        msg = value[1]
        # 1. store into redis server
        ok1 = await self._redis.save_login(user=self._user, content=cmd, msg=msg)
        # 2. save into local storage
        ok2 = await self._dos.save_login_command_message(user=self._user, content=cmd, msg=msg)
        return ok1 or ok2


class LoginTable(DataCache, LoginDBI):
    """ Implementations of LoginDBI """

    def __init__(self, config: Config):
        super().__init__(pool_name='login')  # ID => (LoginCommand, ReliableMessage)
        self._redis = LoginCache(config=config)
        self._dos = LoginStorage(config=config)

    def show_info(self):
        self._dos.show_info()

    def _new_task(self, user: ID) -> CmdTask:
        return CmdTask(user=user,
                       redis=self._redis, storage=self._dos,
                       mutex_lock=self._mutex_lock, cache_pool=self._cache_pool)

    async def _is_expired(self, user: ID, content: LoginCommand) -> bool:
        """ check old record with command time """
        new_time = content.time
        if new_time is None or new_time <= 0:
            return False
        # check old record
        old, _ = await self.load_login_command_message(user=user)
        if old is not None and is_before(old_time=old.time, new_time=new_time):
            # command expired
            return True

    async def load_login_command_message(self, user: ID) -> Tuple[Optional[LoginCommand], Optional[ReliableMessage]]:
        task = self._new_task(user=user)
        pair = await task.load()
        if pair is None:
            return None, None
        return pair

    #
    #   Login DBI
    #

    # Override
    async def save_login_command_message(self, user: ID, content: LoginCommand, msg: ReliableMessage) -> bool:
        #
        #  check command time
        #
        if await self._is_expired(user=user, content=content):
            # command expired, drop it
            return False
        else:
            value = (content, msg)
        #
        #  build task for saving
        #
        task = self._new_task(user=user)
        return await task.save(value=value)

    # Override
    async def get_login_command_message(self, user: ID) -> Tuple[Optional[LoginCommand], Optional[ReliableMessage]]:
        return await self.load_login_command_message(user=user)
