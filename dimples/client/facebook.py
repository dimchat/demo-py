# -*- coding: utf-8 -*-
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

"""
    Facebook for client
    ~~~~~~~~~~~~~~~~~~~

    Barrack for cache entities
"""

from typing import Optional, List

from dimsdk import EntityType
from dimsdk import ID, Document, Bulletin
from dimsdk import User

from ..utils import Runner
from ..common import BroadcastUtils
from ..common import CommonFacebook


# noinspection PyAbstractClass
class ClientFacebook(CommonFacebook):

    # Override
    async def select_user(self, receiver: ID) -> Optional[User]:
        if receiver.is_user:
            return await super().select_user(receiver=receiver)
        # group message(recipient not designated)
        assert receiver.is_group, 'receiver error: %s' % receiver
        # the messenger will check group info before decrypting message,
        # so we can trust that the group's meta & members MUST exist here.
        users = await self.archivist.local_users
        if users is None or len(users) == 0:
            self.error(msg='local users should not be empty')
            return None
        elif receiver.is_broadcast:
            # broadcast message can decrypt by anyone, so just return current user
            return users[0]
        members = await self.get_members(identifier=receiver)
        # assert len(members) > 0, 'members not found: %s' % receiver
        for item in users:
            if item.identifier in members:
                # DISCUSS: set this item to be current user?
                return item

    # Override
    async def save_document(self, document: Document) -> bool:
        ok = await super().save_document(document=document)
        if ok and isinstance(document, Bulletin):
            # check administrators
            array = document.get_property(name='administrators')
            if array is not None:
                group = document.identifier
                assert group.is_group, 'group ID error: %s' % group
                admins = ID.convert(array=array)
                ok = await self.save_administrators(administrators=admins, group=group)
        return ok

    #
    #   Group DataSource
    #

    # Override
    async def get_founder(self, identifier: ID) -> Optional[ID]:
        assert identifier.is_group, 'group ID error: %s' % identifier
        # check broadcast group
        if identifier.is_broadcast:
            # founder of broadcast group
            return BroadcastUtils.broadcast_founder(group=identifier)
        # check bulletin document
        doc = await self.get_bulletin(group=identifier)
        if doc is None:
            # the owner(founder) should be set in the bulletin document of group
            return None
        db = self.database
        # check local storage
        user = await db.get_founder(group=identifier)
        if user is not None:
            # got from local storage
            return user
        # get from bulletin document
        user = doc.founder
        if user is None:
            self.error(msg='founder not designated for group: %s' % identifier)
        return user

    # Override
    async def get_owner(self, identifier: ID) -> Optional[ID]:
        assert identifier.is_group, 'group ID error: %s' % identifier
        # check broadcast group
        if identifier.is_broadcast:
            # owner of broadcast group
            return BroadcastUtils.broadcast_owner(group=identifier)
        # check bulletin document
        doc = await self.get_bulletin(group=identifier)
        if doc is None:
            # the owner(founder) should be set in the bulletin document of group
            return None
        db = self.database
        # check local storage
        user = await db.get_owner(group=identifier)
        if user is not None:
            # got from local storage
            return user
        # check group type
        if identifier.type == EntityType.GROUP:
            # Polylogue's owner is its founder
            user = await db.get_founder(group=identifier)
            if user is None:
                user = doc.founder
        if user is None:
            self.error(msg='owner not found for group: %s' % identifier)
        return user

    # Override
    async def get_members(self, identifier: ID) -> List[ID]:
        assert identifier.is_group, 'group ID error: %s' % identifier
        # check broadcast group
        if identifier.is_broadcast:
            # members of broadcast group
            return BroadcastUtils.broadcast_members(group=identifier)
        # check group owner
        owner = await self.get_owner(identifier=identifier)
        if owner is None:
            self.error(msg='group empty: %s' % identifier)
            return []
        db = self.database
        # check local storage
        users = await db.get_members(group=identifier)
        checker = self.checker
        if checker is not None:
            coro = checker.check_members(group=identifier, members=users)
            Runner.async_task(coro=coro)
        # OK
        if len(users) == 0:
            users = [owner]
        else:
            assert users[0] == owner, 'group owner must be the first member: %s' % identifier
        return users

    # Override
    async def get_assistants(self, identifier: ID) -> List[ID]:
        assert identifier.is_group, 'group ID error: %s' % identifier
        # check bulletin document
        doc = await self.get_bulletin(group=identifier)
        if doc is None:
            # the assistants should be set in the bulletin document of group
            return []
        db = self.database
        # check local storage
        bots = await db.get_assistants(group=identifier)
        if len(bots) > 0:
            # got from local storage
            return bots
        # get from bulletin document
        bots = doc.assistants
        return [] if bots is None else bots

    #
    #   Organizational Structure
    #

    # Override
    async def get_administrators(self, group: ID) -> List[ID]:
        assert group.is_group, 'group ID error: %s' % group
        # check bulletin document
        doc = await self.get_bulletin(group=group)
        # the administrators should be set in the bulletin document
        if doc is None:
            return []
        # the 'administrators' should be saved into local storage
        # when the newest bulletin document received,
        # so we must get them from the local storage only,
        # not from the bulletin document.
        db = self.database
        return await db.get_administrators(group=group)

    # protected
    async def save_administrators(self, administrators: List[ID], group: ID) -> bool:
        db = self.database
        return await db.save_administrators(administrators, group=group)

    # protected
    async def save_members(self, members: List[ID], group: ID) -> bool:
        db = self.database
        return await db.save_members(members, group=group)


# TODO: ANS?
