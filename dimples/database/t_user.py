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
from typing import List

from dimsdk import ID

from ..utils import CacheHolder, CacheManager
from ..common import UserDBI

from .dos import UserStorage


class UserTable(UserDBI):
    """ Implementations of UserDBI """

    def __init__(self, root: str = None, public: str = None, private: str = None):
        super().__init__()
        man = CacheManager()
        self.__user_cache = man.get_pool(name='user')
        self.__user_storage = UserStorage(root=root, public=public, private=private)

    def show_info(self):
        self.__user_storage.show_info()

    #
    #   User DBI
    #

    # Override
    def local_users(self) -> List[ID]:
        """ get local users """
        now = time.time()
        # 1. check memory cache
        value, holder = self.__user_cache.fetch(key='local_users', now=now)
        if value is None:
            # cache empty
            if holder is None:
                # local users not load yet, wait to load
                self.__user_cache.update(key='local_users', life_span=128, now=now)
            else:
                assert isinstance(holder, CacheHolder), 'local users cache error'
                if holder.is_alive(now=now):
                    # local users not exists
                    return []
                # local users expired, wait to reload
                holder.renewal(duration=128, now=now)
            # 2. check local storage
            value = self.__user_storage.local_users()
            # 3. update memory cache
            if value is not None:
                self.__user_cache.update(key='local_users', value=value, life_span=36000, now=now)
        # OK, return cached value
        return value

    # Override
    def contacts(self, identifier: ID) -> List[ID]:
        """ get contacts for user """
        now = time.time()
        # 1. check memory cache
        value, holder = self.__user_cache.fetch(key=identifier, now=now)
        if value is None:
            # cache empty
            if holder is None:
                # contacts not load yet, wait to load
                self.__user_cache.update(key=identifier, life_span=128, now=now)
            else:
                assert isinstance(holder, CacheHolder), 'contacts cache error'
                if holder.is_alive(now=now):
                    # meta not exists
                    return []
                # meta expired, wait to reload
                holder.renewal(duration=128, now=now)
            # 2. check local storage
            value = self.__user_storage.contacts(identifier=identifier)
            # 3. update memory cache
            if value is not None:
                self.__user_cache.update(key=identifier, value=value, life_span=36000, now=now)
        # OK, return cached value
        return value
