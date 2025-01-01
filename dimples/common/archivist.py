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

from dimsdk import VerifyKey, EncryptKey
from dimsdk import ID, EntityType
from dimsdk import User, BaseUser, Station, Bot
from dimsdk import Group, BaseGroup, ServiceProvider
from dimsdk import Facebook
from dimsdk import Archivist
from dimsdk import DocumentUtils

from ..utils import Logging

from .dbi import AccountDBI


class CommonArchivist(Archivist, Logging):

    def __init__(self, facebook: Facebook, database: AccountDBI):
        super().__init__()
        self.__barrack = weakref.ref(facebook)
        self.__database = database
        self.__current: Optional[User] = None

    @property
    def facebook(self) -> Optional[Facebook]:
        return self.__barrack()

    @property
    def database(self) -> AccountDBI:
        return self.__database

    @property
    def current_user(self) -> Optional[User]:
        return self.__current

    @current_user.setter
    def current_user(self, user: User):
        self.__current = user

    # Override
    async def create_user(self, identifier: ID) -> Optional[User]:
        assert identifier.is_user, 'user ID error: %s' % identifier
        # check visa key
        if not identifier.is_broadcast:
            key = await self.facebook.public_key_for_encryption(identifier=identifier)
            if key is None:
                # assert False, 'visa.key not found: %s' % identifier
                return None
            # NOTICE: if visa.key exists, then visa & meta must exist too.
        network = identifier.type
        # check user type
        if network == EntityType.STATION:
            return Station(identifier=identifier)
        elif network == EntityType.BOT:
            return Bot(identifier=identifier)
        # general user, or 'anyone@anywhere'
        return BaseUser(identifier=identifier)

    # Override
    async def create_group(self, identifier: ID) -> Optional[Group]:
        assert identifier.is_group, 'group ID error: %s' % identifier
        # check members
        if not identifier.is_broadcast:
            members = await self.facebook.get_members(identifier=identifier)
            if members is None or len(members) == 0:
                # assert False, 'group members not found: %s' % identifier
                return None
            # NOTICE: if members exist, then owner (founder) must exist,
            #         and bulletin & meta must exist too.
        network = identifier.type
        # check group type
        if network == EntityType.ISP:
            return ServiceProvider(identifier=identifier)
        # general group, or 'everyone@everhwhere'
        return BaseGroup(identifier=identifier)

    # Override
    async def get_meta_key(self, identifier: ID) -> Optional[VerifyKey]:
        meta = await self.facebook.get_meta(identifier=identifier)
        if meta is not None:
            return meta.public_key

    # Override
    async def get_visa_key(self, identifier: ID) -> Optional[EncryptKey]:
        docs = await self.facebook.get_documents(identifier=identifier)
        if docs is not None:
            visa = DocumentUtils.last_visa(documents=docs)
            if visa is not None:
                return visa.public_key

    @property  # Override
    async def local_users(self) -> List[User]:
        all_users = []
        facebook = self.facebook
        array = await self.database.get_local_users()
        if facebook is not None and array is not None:
            for item in array:
                # assert await facebook.private_key_for_signature(identifier=item) is not None
                user = await facebook.get_user(identifier=item)
                if user is not None:
                    all_users.append(user)
                else:
                    assert False, 'failed to create user: %s' % item
        if len(all_users) == 0:
            current = self.__current
            if current is not None:
                all_users.append(current)
            else:
                self.error(msg='failed to get local users')
        return all_users
