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
from typing import Optional, List

from aiou.mem import CachePool

from dimsdk import DateTime
from dimsdk import PrivateKey, DecryptKey, SignKey
from dimsdk import ID

from ..utils import Config
from ..utils import SharedCacheManager
from ..common import PrivateKeyDBI

from .dos import PrivateKeyStorage

from .t_base import DbTask


# noinspection PyAbstractClass
class PriKeyTask(DbTask):

    MEM_CACHE_EXPIRES = 36000  # seconds
    MEM_CACHE_REFRESH = 32     # seconds

    def __init__(self, user: ID,
                 storage: PrivateKeyStorage,
                 mutex_lock: threading.Lock, cache_pool: CachePool):
        super().__init__(mutex_lock=mutex_lock, cache_pool=cache_pool,
                         cache_expires=self.MEM_CACHE_EXPIRES,
                         cache_refresh=self.MEM_CACHE_REFRESH)
        self._user = user
        self._dos = storage

    @property  # Override
    def cache_key(self) -> ID:
        return self._user


class IdKeyTask(PriKeyTask):

    # Override
    async def _read_data(self) -> Optional[SignKey]:
        return await self._dos.private_key_for_visa_signature(user=self._user)

    # Override
    async def _write_data(self, value: SignKey) -> bool:
        pass


class MsgKeyTask(PriKeyTask):

    # Override
    async def _read_data(self) -> Optional[List[DecryptKey]]:
        return await self._dos.private_keys_for_decryption(user=self._user)

    # Override
    async def _write_data(self, value: List[DecryptKey]) -> bool:
        pass


class PrivateKeyTable(PrivateKeyDBI):
    """ Implementations of PrivateKeyDBI """

    def __init__(self, config: Config):
        super().__init__()
        man = SharedCacheManager()
        self._id_key_cache = man.get_pool(name='private_id_key')      # ID => PrivateKey
        self._msg_keys_cache = man.get_pool(name='private_msg_keys')  # ID => List[PrivateKey]
        self._dos = PrivateKeyStorage(config=config)
        self._lock = threading.Lock()

    def show_info(self):
        self._dos.show_info()

    def _new_id_key_task(self, user: ID) -> IdKeyTask:
        return IdKeyTask(user=user,
                         storage=self._dos,
                         mutex_lock=self._lock, cache_pool=self._id_key_cache)

    def _new_msg_key_task(self, user: ID) -> MsgKeyTask:
        return MsgKeyTask(user=user,
                          storage=self._dos,
                          mutex_lock=self._lock, cache_pool=self._msg_keys_cache)

    async def _add_decrypt_key(self, key: PrivateKey, user: ID) -> Optional[List[PrivateKey]]:
        private_keys = await self.private_keys_for_decryption(user=user)
        private_keys = PrivateKeyDBI.convert_private_keys(keys=private_keys)
        return PrivateKeyDBI.insert(item=key, array=private_keys)

    #
    #   Private Key DBI
    #

    # Override
    async def save_private_key(self, key: PrivateKey, user: ID, key_type: str = 'M') -> bool:
        #
        #  check key type
        #
        if key_type == PrivateKeyStorage.ID_KEY_TAG:
            # update 'id_key'
            value = key
            cache_pool = self._id_key_cache
        else:
            # add to old keys
            private_keys = self._add_decrypt_key(key=key, user=user)
            if private_keys is None:
                # key already exists, nothing changed
                return False
            value = private_keys
            cache_pool = self._msg_keys_cache
        #
        #  lock to update
        #
        now = DateTime.now()
        with self._lock:
            # store into memory cache
            cache_pool.update(key=user, value=value, life_span=PriKeyTask.MEM_CACHE_EXPIRES, now=now)
            # save into local storage
            return await self._dos.save_private_key(key=key, user=user, key_type=key_type)

    # Override
    async def private_keys_for_decryption(self, user: ID) -> List[DecryptKey]:
        """ get sign key for ID """
        task = self._new_msg_key_task(user=user)
        keys = await task.load()
        return [] if keys is None else keys

    # Override
    async def private_key_for_signature(self, user: ID) -> Optional[SignKey]:
        # TODO: support multi private keys
        return await self.private_key_for_visa_signature(user=user)

    # Override
    async def private_key_for_visa_signature(self, user: ID) -> Optional[SignKey]:
        """ get sign key for ID """
        task = self._new_id_key_task(user=user)
        return await task.load()
