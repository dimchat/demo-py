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
from dimsdk import ID, Meta, Bulletin
from dimsdk import Document, DocumentHelper
from dimsdk import GroupDataSource
from dimsdk import TwinsHelper

from ..utils import Logging
from ..common import CommonFacebook, CommonMessenger
from ..common import AccountDBI


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

    @property
    def database(self) -> AccountDBI:
        return self.facebook.database

    def build_group_name(self, members: List[ID]) -> str:
        count = len(members)
        if count > 0:
            facebook = self.facebook
            text = facebook.get_name(identifier=members[0])
            for i in range(1, count):
                nickname = facebook.get_name(identifier=members[i])
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
    def meta(self, identifier: ID) -> Optional[Meta]:
        info = self.facebook.meta(identifier=identifier)
        if info is None:
            # if not found, query it from any station
            self.messenger.query_meta(identifier=identifier)
        return info

    # Override
    def documents(self, identifier: ID) -> List[Document]:
        docs = self.facebook.documents(identifier=identifier)
        if len(docs) == 0:
            # if not found, query it from any station
            self.messenger.query_document(identifier=identifier)
        return docs

    def bulletin(self, group: ID) -> Optional[Bulletin]:
        docs = self.documents(identifier=group)
        return DocumentHelper.last_bulletin(documents=docs)

    def save_document(self, document: Document) -> bool:
        return self.facebook.save_document(document=document)

    #
    #   Group DataSource
    #

    # Override
    def founder(self, identifier: ID) -> Optional[ID]:
        assert identifier.is_group, 'ID error: %s' % identifier
        doc = self.bulletin(identifier)
        if doc is None:
            # the owner(founder) should be set in the bulletin document of group
            return None
        return self.facebook.founder(identifier=identifier)

    # Override
    def owner(self, identifier: ID) -> Optional[ID]:
        assert identifier.is_group, 'ID error: %s' % identifier
        doc = self.bulletin(identifier)
        if doc is None:
            # the owner(founder) should be set in the bulletin document of group
            return None
        return self.facebook.owner(identifier=identifier)

    # Override
    def assistants(self, identifier: ID) -> List[ID]:
        assert identifier.is_group, 'ID error: %s' % identifier
        doc = self.bulletin(identifier)
        if doc is None:
            # the group assistants should be set in the bulletin document
            return []
        return self.facebook.assistants(identifier=identifier)

    # Override
    def members(self, identifier: ID) -> List[ID]:
        assert identifier.is_group, 'ID error: %s' % identifier
        doc = self.bulletin(identifier)
        if doc is None:
            # group not ready
            return []
        members = self.facebook.members(identifier=identifier)
        if len(members) < 2:
            # members not found, query the owner (or group bots)
            self.messenger.query_members(identifier=identifier)
        return members

    def save_members(self, members: List[ID], group: ID) -> bool:
        return self.database.save_members(members=members, group=group)

    #
    #   Administrators
    #

    def administrators(self, group: ID) -> List[ID]:
        assert group.is_group, 'ID error: %s' % group
        doc = self.bulletin(group)
        if doc is None:
            # group not ready
            return []
        admins = self.database.administrators(group=group)
        if len(admins) > 0:
            # got from database
            return admins
        array = doc.get_property(key='administrators')
        return [] if array is None else ID.convert(array=array)

    def save_administrators(self, administrators: List[ID], group: ID) -> bool:
        return self.database.save_administrators(administrators=administrators, group=group)

    #
    #   Membership
    #

    def is_founder(self, user: ID, group: ID) -> bool:
        assert user.is_user and group.is_group, 'ID error: %s, %s' % (user, group)
        founder = self.founder(identifier=group)
        if founder is not None:
            return founder == user
        # check member's public key with group's meta.key
        g_meta = self.meta(identifier=group)
        m_meta = self.meta(identifier=user)
        if g_meta is None or m_meta is None:
            self.warning(msg='failed to get meta for group: %s, user: %s' % (group, user))
            return False
        return g_meta.match_public_key(key=m_meta.public_key)

    def is_owner(self, user: ID, group: ID) -> bool:
        assert user.is_user and group.is_group, 'ID error: %s, %s' % (user, group)
        owner = self.owner(identifier=group)
        if owner is not None:
            return owner == user
        if group.type == EntityType.GROUP:
            # this is a polylogue
            return self.is_founder(user=user, group=group)
        raise Exception('only polylogue so far')

    def is_member(self, user: ID, group: ID) -> bool:
        assert user.is_user and group.is_group, 'ID error: %s, %s' % (user, group)
        members = self.members(identifier=group)
        return user in members

    def is_administrator(self, user: ID, group: ID) -> bool:
        assert user.is_user and group.is_group, 'ID error: %s, %s' % (user, group)
        admins = self.administrators(group=group)
        return user in admins

    def is_assistant(self, user: ID, group: ID) -> bool:
        assert user.is_user and group.is_group, 'ID error: %s, %s' % (user, group)
        bots = self.assistants(identifier=group)
        return user in bots
