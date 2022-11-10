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

import time
from typing import Optional, List

from dimsdk import PrivateKey, DecryptKey, SignKey
from dimsdk import ID

from ..utils import CacheHolder, CacheManager
from ..common import PrivateKeyDBI

from .dos import PrivateKeyStorage
from .dos.private import insert_key


class PrivateKeyTable(PrivateKeyDBI):
    """ Implementations of PrivateKeyDBI """

    def __init__(self, root: str = None, public: str = None, private: str = None):
        super().__init__()
        man = CacheManager()
        self.__id_key_cache = man.get_pool(name='private_id_key')
        self.__msg_keys_cache = man.get_pool(name='private_msg_keys')
        self.__key_storage = PrivateKeyStorage(root=root, public=public, private=private)

    def show_info(self):
        self.__key_storage.show_info()

    #
    #   PrivateKey DBI
    #

    # Override
    def save_private_key(self, key: PrivateKey, identifier: ID, key_type: str = 'M') -> bool:
        now = time.time()
        # 1. update memory cache
        if key_type == PrivateKeyStorage.ID_KEY_TAG:
            # update 'id_key'
            self.__id_key_cache.update(key=identifier, value=key, life_span=36000, now=now)
        else:
            # add to old keys
            private_keys = self.private_keys_for_decryption(identifier=identifier)
            private_keys = insert_key(key=key, private_keys=private_keys)
            if private_keys is None:
                # key already exists, nothing changed
                return False
            # update 'msg_keys'
            self.__msg_keys_cache.update(key=identifier, value=private_keys, life_span=36000, now=now)
        # 2. update local storage
        return self.__key_storage.save_private_key(key=key, identifier=identifier, key_type=key_type)

    # Override
    def private_keys_for_decryption(self, identifier: ID) -> List[DecryptKey]:
        """ get sign key for ID """
        now = time.time()
        # 1. check memory cache
        value, holder = self.__msg_keys_cache.fetch(key=identifier, now=now)
        if value is None:
            # cache empty
            if holder is None:
                # msg keys not load yet, wait to load
                self.__msg_keys_cache.update(key=identifier, life_span=128, now=now)
            else:
                assert isinstance(holder, CacheHolder), 'msg keys cache error'
                if holder.is_alive(now=now):
                    # msg keys not exists
                    return []
                # msg keys expired, wait to reload
                holder.renewal(duration=128, now=now)
            # 2. check local storage
            value = self.__key_storage.private_keys_for_decryption(identifier=identifier)
            # 3. update memory cache
            if value is not None:
                self.__msg_keys_cache.update(key=identifier, value=value, life_span=36000, now=now)
        # OK, return cached value
        return value

    # Override
    def private_key_for_signature(self, identifier: ID) -> Optional[SignKey]:
        # TODO: support multi private keys
        return self.private_key_for_visa_signature(identifier=identifier)

    # Override
    def private_key_for_visa_signature(self, identifier: ID) -> Optional[SignKey]:
        """ get sign key for ID """
        now = time.time()
        # 1. check memory cache
        value, holder = self.__id_key_cache.fetch(key=identifier, now=now)
        if value is None:
            # cache empty
            if holder is None:
                # id key not load yet, wait to load
                self.__id_key_cache.update(key=identifier, life_span=128, now=now)
            else:
                assert isinstance(holder, CacheHolder), 'id key cache error'
                if holder.is_alive(now=now):
                    # id key not exists
                    return None
                # id key expired, wait to reload
                holder.renewal(duration=128, now=now)
            # 2. check local storage
            value = self.__key_storage.private_key_for_visa_signature(identifier=identifier)
            # 3. update memory cache
            if value is not None:
                self.__id_key_cache.update(key=identifier, value=value, life_span=36000, now=now)
        # OK, return cached value
        return value
