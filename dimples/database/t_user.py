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
from typing import List, Optional

from dimsdk import ID

from ..utils import CacheManager
from ..common import UserDBI, ContactDBI

from .dos import UserStorage


class UserTable(UserDBI, ContactDBI):
    """ Implementations of UserDBI """

    def __init__(self, root: str = None, public: str = None, private: str = None):
        super().__init__()
        man = CacheManager()
        self.__dim_cache = man.get_pool(name='dim')            # 'local_users' => List[ID]
        self.__contacts_cache = man.get_pool(name='contacts')  # ID => List[ID]
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
        value, holder = self.__dim_cache.fetch(key='local_users', now=now)
        if value is None:
            # cache empty
            if holder is None:
                # local users not load yet, wait to load
                self.__dim_cache.update(key='local_users', life_span=128, now=now)
            else:
                if holder.is_alive(now=now):
                    # local users not exists
                    return []
                # local users expired, wait to reload
                holder.renewal(duration=128, now=now)
            # 2. check local storage
            value = self.__user_storage.local_users()
            # 3. update memory cache
            self.__dim_cache.update(key='local_users', value=value, life_span=36000, now=now)
        # OK, return cached value
        return value

    # Override
    def save_local_users(self, users: List[ID]) -> bool:
        # 1. store into memory cache
        self.__dim_cache.update(key='local_users', value=users, life_span=36000)
        # 2. store into local storage
        return self.__user_storage.save_local_users(users=users)

    # Override
    def add_user(self, user: ID) -> bool:
        array = self.local_users()
        if user in array:
            # self.warning(msg='user exists: %s, %s' % (user, array))
            return True
        array.insert(0, user)
        return self.save_local_users(users=array)

    # Override
    def remove_user(self, user: ID) -> bool:
        array = self.local_users()
        if user not in array:
            # self.warning(msg='user not exists: %s, %s' % (user, array))
            return True
        array.remove(user)
        return self.save_local_users(users=array)

    # Override
    def current_user(self) -> Optional[ID]:
        array = self.local_users()
        if len(array) > 0:
            return array[0]

    # Override
    def set_current_user(self, user: ID) -> bool:
        array = self.local_users()
        if user in array:
            index = array.index(user)
            if index == 0:
                # self.warning(msg='current user not changed: %s, %s' % (user, array))
                return True
            array.pop(index)
        array.insert(0, user)
        return self.save_local_users(users=array)

    #
    #   Contact DBI
    #

    # Override
    def contacts(self, user: ID) -> List[ID]:
        """ get contacts for user """
        now = time.time()
        # 1. check memory cache
        value, holder = self.__contacts_cache.fetch(key=user, now=now)
        if value is None:
            # cache empty
            if holder is None:
                # contacts not load yet, wait to load
                self.__contacts_cache.update(key=user, life_span=128, now=now)
            else:
                if holder.is_alive(now=now):
                    # contacts not exists
                    return []
                # contacts expired, wait to reload
                holder.renewal(duration=128, now=now)
            # 2. check local storage
            value = self.__user_storage.contacts(user=user)
            # 3. update memory cache
            self.__contacts_cache.update(key=user, value=value, life_span=36000, now=now)
        # OK, return cached value
        return value

    # Override
    def save_contacts(self, contacts: List[ID], user: ID) -> bool:
        # 1. store into memory cache
        self.__contacts_cache.update(key=user, value=contacts, life_span=36000)
        # 2. store into local storage
        return self.__user_storage.save_contacts(contacts=contacts, user=user)

    # Override
    def add_contact(self, contact: ID, user: ID) -> bool:
        array = self.contacts(user=user)
        if contact in array:
            # self.warning(msg='contact exists: %s, user: %s' % (contact, user))
            return True
        array.append(contact)
        return self.save_contacts(contacts=array, user=user)

    # Override
    def remove_contact(self, contact: ID, user: ID) -> bool:
        array = self.contacts(user=user)
        if contact not in array:
            # self.warning(msg='contact not exists: %s, user: %s' % (contact, user))
            return True
        array.remove(contact)
        return self.save_contacts(contacts=array, user=user)
