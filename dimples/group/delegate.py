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

from typing import Optional, List

from dimsdk import EntityType
from dimsdk import ID, Meta, Document, Bulletin
from dimsdk import GroupDataSource
from dimsdk import TwinsHelper

from ..utils import Logging
from ..common import CommonFacebook, CommonMessenger


def get_facebook(helper: TwinsHelper):
    facebook = helper.facebook
    from ..client import ClientFacebook
    assert isinstance(facebook, ClientFacebook), 'client facebook error: %s' % facebook
    return facebook


class GroupDelegate(TwinsHelper, GroupDataSource, Logging):

    @property  # Override
    def facebook(self) -> CommonFacebook:
        barrack = super().facebook
        assert isinstance(barrack, CommonFacebook), 'facebook error: %s' % barrack
        return barrack

    @property  # Override
    def messenger(self) -> CommonMessenger:
        transceiver = super().messenger
        assert isinstance(transceiver, CommonMessenger), 'messenger error: %s' % transceiver
        return transceiver

    async def build_group_name(self, members: List[ID]) -> str:
        count = len(members)
        if count > 0:
            facebook = self.facebook
            text = await facebook.get_name(identifier=members[0])
            for i in range(1, count):
                nickname = await facebook.get_name(identifier=members[i])
                if len(nickname) == 0:
                    continue
                text += ', %s' % nickname
                if len(text) > 32:
                    text = text[:28]
                    return '%s ...' % text
            # OK
            return text
        assert False, 'members should not be empty here'

    #
    #   Entity DataSource
    #

    # Override
    async def get_meta(self, identifier: ID) -> Optional[Meta]:
        return await self.facebook.get_meta(identifier=identifier)

    # Override
    async def get_documents(self, identifier: ID) -> List[Document]:
        return await self.facebook.get_documents(identifier=identifier)

    async def get_bulletin(self, identifier: ID) -> Optional[Bulletin]:
        assert identifier.is_group, 'group ID error: %s' % identifier
        return await self.facebook.get_bulletin(identifier=identifier)

    async def save_document(self, document: Document) -> bool:
        return await self.facebook.save_document(document=document)

    #
    #   Group DataSource
    #

    # Override
    async def get_founder(self, identifier: ID) -> Optional[ID]:
        assert identifier.is_group, 'group ID error: %s' % identifier
        return await self.facebook.get_founder(identifier=identifier)

    # Override
    async def get_owner(self, identifier: ID) -> Optional[ID]:
        assert identifier.is_group, 'group ID error: %s' % identifier
        return await self.facebook.get_owner(identifier=identifier)

    # Override
    async def get_assistants(self, identifier: ID) -> List[ID]:
        assert identifier.is_group, 'group ID error: %s' % identifier
        return await self.facebook.get_assistants(identifier=identifier)

    # Override
    async def get_members(self, identifier: ID) -> List[ID]:
        assert identifier.is_group, 'group ID error: %s' % identifier
        return await self.facebook.get_members(identifier=identifier)

    async def save_members(self, members: List[ID], group: ID) -> bool:
        assert group.is_group, 'group ID error: %s' % group
        facebook = get_facebook(helper=self)
        return await facebook.save_members(members=members, group=group)

    #
    #   Administrators
    #

    async def get_administrators(self, group: ID) -> List[ID]:
        assert group.is_group, 'group ID error: %s' % group
        facebook = get_facebook(helper=self)
        return await facebook.get_administrators(group=group)

    async def save_administrators(self, administrators: List[ID], group: ID) -> bool:
        assert group.is_group, 'group ID error: %s' % group
        facebook = get_facebook(helper=self)
        return await facebook.save_administrators(administrators, group=group)

    #
    #   Membership
    #

    async def is_founder(self, user: ID, group: ID) -> bool:
        assert user.is_user and group.is_group, 'ID error: %s, %s' % (user, group)
        founder = await self.get_founder(identifier=group)
        if founder is not None:
            return founder == user
        # check member's public key with group's meta.key
        g_meta = await self.get_meta(identifier=group)
        m_meta = await self.get_meta(identifier=user)
        if g_meta is None or m_meta is None:
            self.warning(msg='failed to get meta for group: %s, user: %s' % (group, user))
            return False
        return g_meta.match_public_key(key=m_meta.public_key)

    async def is_owner(self, user: ID, group: ID) -> bool:
        assert user.is_user and group.is_group, 'ID error: %s, %s' % (user, group)
        owner = await self.get_owner(identifier=group)
        if owner is not None:
            return owner == user
        if group.type == EntityType.GROUP:
            # this is a polylogue
            return await self.is_founder(user=user, group=group)
        raise Exception('only polylogue so far')

    async def is_member(self, user: ID, group: ID) -> bool:
        assert user.is_user and group.is_group, 'ID error: %s, %s' % (user, group)
        members = await self.get_members(identifier=group)
        return user in members

    async def is_administrator(self, user: ID, group: ID) -> bool:
        assert user.is_user and group.is_group, 'ID error: %s, %s' % (user, group)
        admins = await self.get_administrators(group=group)
        return user in admins

    async def is_assistant(self, user: ID, group: ID) -> bool:
        assert user.is_user and group.is_group, 'ID error: %s, %s' % (user, group)
        bots = await self.get_assistants(identifier=group)
        return user in bots
