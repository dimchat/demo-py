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

from abc import ABC
from typing import Optional, List

from dimsdk import ID
from dimsdk import User, Group

from ..common import CommonArchivist, CommonFacebook

from ..group import SharedGroupManager


class ClientArchivist(CommonArchivist, ABC):

    # Override
    async def create_group(self, identifier: ID) -> Optional[Group]:
        group = await super().create_group(identifier=identifier)
        if group is not None:
            delegate = group.data_source
            if delegate is None or delegate is self.facebook:
                # replace group's data source
                group.data_source = SharedGroupManager()
        return group

    @property  # Override
    async def local_users(self) -> List[User]:
        users = await super().local_users
        if len(users) > 0:
            return users
        facebook = self.facebook
        if isinstance(facebook, CommonFacebook):
            current = await facebook.current_user
            if current is not None:
                return [current]
        self.error(msg='failed to get local users')
        return []
