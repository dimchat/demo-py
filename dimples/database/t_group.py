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
from ..common import GroupDBI

from .dos import GroupStorage


class GroupTable(GroupDBI):
    """ Implementations of GroupDBI """

    def __init__(self, root: str = None, public: str = None, private: str = None):
        super().__init__()
        man = CacheManager()
        self.__founder_cache = man.get_pool(name='group.founder')        # ID => ID
        self.__owner_cache = man.get_pool(name='group.owner')            # ID => ID
        self.__members_cache = man.get_pool(name='group.members')        # ID => List[ID]
        self.__assistants_cache = man.get_pool(name='group.assistants')  # ID => List[ID]
        self.__group_storage = GroupStorage(root=root, public=public, private=private)

    def show_info(self):
        self.__group_storage.show_info()

    #
    #   Group DBI
    #

    # Override
    def founder(self, group: ID) -> Optional[ID]:
        """ get founder of group """
        now = time.time()
        # 1. check memory cache
        value, holder = self.__founder_cache.fetch(key=group, now=now)
        if value is None:
            # cache empty
            if holder is None:
                # founder not load yet, wait to load
                self.__founder_cache.update(key=group, life_span=128, now=now)
            else:
                if holder.is_alive(now=now):
                    # founder not exists
                    return None
                # founder expired, wait to reload
                holder.renewal(duration=128, now=now)
            # 2. check local storage
            value = self.__group_storage.founder(group=group)
            # 3. update memory cache
            if value is None:
                self.__founder_cache.update(key=group, value=value, life_span=600, now=now)
            else:
                self.__founder_cache.update(key=group, value=value, life_span=36000, now=now)
        # OK, return cached value
        return value

    # Override
    def owner(self, group: ID) -> Optional[ID]:
        """ get owner of group """
        now = time.time()
        # 1. check memory cache
        value, holder = self.__owner_cache.fetch(key=group, now=now)
        if value is None:
            # cache empty
            if holder is None:
                # owner not load yet, wait to load
                self.__owner_cache.update(key=group, life_span=128, now=now)
            else:
                if holder.is_alive(now=now):
                    # owner not exists
                    return None
                # owner expired, wait to reload
                holder.renewal(duration=128, now=now)
            # 2. check local storage
            value = self.__group_storage.owner(group=group)
            # 3. update memory cache
            self.__owner_cache.update(key=group, value=value, life_span=600, now=now)
        # OK, return cached value
        return value

    # Override
    def members(self, group: ID) -> List[ID]:
        """ get members of group """
        now = time.time()
        # 1. check memory cache
        value, holder = self.__members_cache.fetch(key=group, now=now)
        if value is None:
            # cache empty
            if holder is None:
                # members not load yet, wait to load
                self.__members_cache.update(key=group, life_span=128, now=now)
            else:
                if holder.is_alive(now=now):
                    # members not exists
                    return []
                # members expired, wait to reload
                holder.renewal(duration=128, now=now)
            # 2. check local storage
            value = self.__group_storage.members(group=group)
            # 3. update memory cache
            self.__members_cache.update(key=group, value=value, life_span=600, now=now)
        # OK, return cached value
        return value

    # Override
    def save_members(self, members: List[ID], group: ID) -> bool:
        # 1. store into memory cache
        self.__members_cache.update(key=group, value=members, life_span=600)
        # 2. store into local storage
        return self.__group_storage.save_members(members=members, group=group)

    # Override
    def assistants(self, group: ID) -> List[ID]:
        """ get assistants of group """
        now = time.time()
        # 1. check memory cache
        value, holder = self.__assistants_cache.fetch(key=group, now=now)
        if value is None:
            # cache empty
            if holder is None:
                # assistants not load yet, wait to load
                self.__assistants_cache.update(key=group, life_span=128, now=now)
            else:
                if holder.is_alive(now=now):
                    # assistants not exists
                    return []
                # assistants expired, wait to reload
                holder.renewal(duration=128, now=now)
            # 2. check local storage
            value = self.__group_storage.assistants(group=group)
            # 3. update memory cache
            self.__assistants_cache.update(key=group, value=value, life_span=600, now=now)
        # OK, return cached value
        return value

    # Override
    def save_assistants(self, assistants: List[ID], group: ID) -> bool:
        # 1. store into memory cache
        self.__assistants_cache.update(key=group, value=assistants, life_span=600)
        # 2. store into local storage
        return self.__group_storage.save_assistants(assistants=assistants, group=group)
