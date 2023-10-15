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

from typing import List

from dimsdk import DateTime
from dimsdk import ID

from ..utils import CacheManager
from ..common import UserDBI

from .dos import UserStorage


class UserTable(UserDBI):
    """ Implementations of UserDBI """

    CACHE_EXPIRES = 300    # seconds
    CACHE_REFRESHING = 32  # seconds

    def __init__(self, root: str = None, public: str = None, private: str = None):
        super().__init__()
        self.__dos = UserStorage(root=root, public=public, private=private)
        man = CacheManager()
        self.__contacts_cache = man.get_pool(name='contacts')  # ID => List[ID]

    def show_info(self):
        self.__dos.show_info()

    #
    #   User DBI
    #

    # Override
    def local_users(self) -> List[ID]:
        return []

    # Override
    def save_local_users(self, users: List[ID]) -> bool:
        pass

    #
    #   Contact DBI
    #

    # Override
    def contacts(self, user: ID) -> List[ID]:
        """ get contacts for user """
        now = DateTime.now()
        # 1. check memory cache
        value, holder = self.__contacts_cache.fetch(key=user, now=now)
        if value is None:
            # cache empty
            if holder is None:
                # contacts not load yet, wait to load
                self.__contacts_cache.update(key=user, life_span=self.CACHE_REFRESHING, now=now)
            else:
                if holder.is_alive(now=now):
                    # contacts not exists
                    return []
                # contacts expired, wait to reload
                holder.renewal(duration=self.CACHE_REFRESHING, now=now)
            # 2. check local storage
            value = self.__dos.contacts(user=user)
            # 3. update memory cache
            self.__contacts_cache.update(key=user, value=value, life_span=self.CACHE_EXPIRES, now=now)
        # OK, return cached value
        return value

    # Override
    def save_contacts(self, contacts: List[ID], user: ID) -> bool:
        # 1. store into memory cache
        self.__contacts_cache.update(key=user, value=contacts, life_span=self.CACHE_EXPIRES)
        # 2. store into local storage
        return self.__dos.save_contacts(contacts=contacts, user=user)
