# -*- coding: utf-8 -*-
#
#   DIM-SDK : Decentralized Instant Messaging Software Development Kit
#
#                                Written in 2023 by Moky <albert.moky@gmail.com>
#
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

import weakref
from typing import List, Optional

from dimsdk import ID
from dimsdk import User, Group
from dimsdk import Facebook
from dimsdk import Barrack

from ..utils import Logging
from ..utils import ThanosCache

from .dbi import AccountDBI


class CommonArchivist(Barrack, Logging):

    def __init__(self, facebook: Facebook, database: AccountDBI):
        super().__init__()
        self.__barrack = weakref.ref(facebook)
        self.__database = database
        # memory caches
        self.__user_cache = ThanosCache()   # ID -> User
        self.__group_cache = ThanosCache()  # ID -> Group

    @property
    def facebook(self) -> Optional[Facebook]:
        return self.__barrack()

    @property
    def database(self) -> AccountDBI:
        return self.__database

    def reduce_memory(self):
        cnt1 = self.__user_cache.reduce_memory()
        cnt2 = self.__group_cache.reduce_memory()
        return cnt1 + cnt2

    #
    #   Barrack
    #

    # Override
    def cache_user(self, user: User):
        if user.data_source is None:
            user.data_source = self.facebook
        self.__user_cache.put(key=user.identifier, value=user)

    # Override
    def cache_group(self, group: Group):
        if group.data_source is None:
            group.data_source = self.facebook
        self.__group_cache.put(key=group.identifier, value=group)

    # Override
    def get_user(self, identifier: ID):
        return self.__user_cache.get(key=identifier)

    # Override
    def get_group(self, identifier: ID):
        return self.__group_cache.get(key=identifier)

    @property  # Override
    async def local_users(self) -> List[User]:
        facebook = self.facebook
        array = await self.database.get_local_users()
        if facebook is None or array is None:
            return []
        all_users = []
        for item in array:
            # assert await facebook.private_key_for_signature(identifier=item) is not None
            user = await facebook.get_user(identifier=item)
            if user is not None:
                all_users.append(user)
            else:
                assert False, 'failed to create user: %s' % item
        return all_users
