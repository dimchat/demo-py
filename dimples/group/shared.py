# -*- coding: utf-8 -*-
#
#   DIM-SDK : Decentralized Instant Messaging Software Development Kit
#
#                                Written in 2024 by Moky <albert.moky@gmail.com>
#
# ==============================================================================
# MIT License
#
# Copyright (c) 2024 Albert Moky
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

from dimsdk import Singleton
from dimsdk import ID, Meta, Document, Bulletin
from dimsdk import GroupDataSource
from dimsdk import InstantMessage, ReliableMessage

from ..common import CommonFacebook, CommonMessenger

from .delegate import GroupDelegate
from .manager import GroupManager
from .admin import AdminManager
from .emitter import GroupEmitter


@Singleton
class SharedGroupManager(GroupDataSource):

    def __init__(self):
        super().__init__()
        self.__barrack = None
        self.__transceiver = None
        # delegates
        self.__delegate = None
        self.__manager = None
        self.__admin_manager = None
        self.__emitter = None

    def _clear_delegates(self):
        self.__delegate = None
        self.__manager = None
        self.__admin_manager = None
        self.__emitter = None

    @property
    def facebook(self) -> Optional[CommonFacebook]:
        ref = self.__barrack
        if ref is not None:
            return ref()

    @facebook.setter
    def facebook(self, barrack: CommonFacebook):
        self.__barrack = None if barrack is None else weakref.ref(barrack)
        self._clear_delegates()

    @property
    def messenger(self) -> Optional[CommonMessenger]:
        ref = self.__transceiver
        if ref is not None:
            return ref()

    @messenger.setter
    def messenger(self, transceiver: CommonMessenger):
        self.__transceiver = None if transceiver is None else weakref.ref(transceiver)
        self._clear_delegates()

    #
    #   Delegates
    #

    @property
    def delegate(self) -> GroupDelegate:
        target = self.__delegate
        if target is None:
            self.__delegate = target = GroupDelegate(facebook=self.facebook, messenger=self.messenger)
        return target

    @property
    def manager(self) -> GroupManager:
        target = self.__manager
        if target is None:
            self.__manager = target = GroupManager(delegate=self.delegate)
        return target

    @property
    def admin_manager(self) -> AdminManager:
        target = self.__admin_manager
        if target is None:
            self.__admin_manager = target = AdminManager(delegate=self.delegate)
        return target

    @property
    def emitter(self) -> GroupEmitter:
        target = self.__emitter
        if target is None:
            self.__emitter = target = GroupEmitter(delegate=self.delegate)
        return target

    async def build_group_name(self, members: List[ID]) -> str:
        delegate = self.delegate
        return await delegate.build_group_name(members=members)

    #
    #   Entity DataSource
    #

    # Override
    async def get_meta(self, identifier: ID) -> Optional[Meta]:
        delegate = self.delegate
        return await delegate.get_meta(identifier=identifier)

    # Override
    async def get_documents(self, identifier: ID) -> List[Document]:
        delegate = self.delegate
        return await delegate.get_documents(identifier=identifier)

    async def get_bulletin(self, group: ID) -> Optional[Bulletin]:
        delegate = self.delegate
        return await delegate.get_bulletin(identifier=group)

    #
    #   Group DataSource
    #

    # Override
    async def get_founder(self, identifier: ID) -> Optional[ID]:
        delegate = self.delegate
        return await delegate.get_founder(identifier=identifier)

    # Override
    async def get_owner(self, identifier: ID) -> Optional[ID]:
        delegate = self.delegate
        return await delegate.get_owner(identifier=identifier)

    # Override
    async def get_members(self, identifier: ID) -> List[ID]:
        delegate = self.delegate
        return await delegate.get_members(identifier=identifier)

    # Override
    async def get_assistants(self, identifier: ID) -> List[ID]:
        delegate = self.delegate
        return await delegate.get_assistants(identifier=identifier)

    async def get_administrators(self, group: ID) -> List[ID]:
        delegate = self.delegate
        return await delegate.get_administrators(group=group)

    async def is_owner(self, user: ID, group: ID) -> bool:
        delegate = self.delegate
        return await delegate.is_owner(user=user, group=group)

    async def broadcast_group_document(self, document: Bulletin) -> bool:
        delegate = self.admin_manager
        return await delegate.broadcast_document(document=document)

    #
    #   Group Manage
    #

    async def create_group(self, members: List[ID]) -> Optional[ID]:
        """ Create new group with members """
        delegate = self.manager
        return await delegate.create_group(members=members)

    async def update_administrators(self, administrators: List[ID], group: ID) -> bool:
        """
        Update 'administrators' in bulletin document

        :param administrators: new admins
        :param group:          group ID
        :return: True on success
        """
        delegate = self.admin_manager
        return await delegate.update_administrators(administrators=administrators, group=group)

    async def reset_group_members(self, members: List[ID], group: ID) -> bool:
        """
        Reset group members

        :param members: new members
        :param group:   group ID
        :return: True on success
        """
        delegate = self.manager
        return await delegate.reset_members(members=members, group=group)

    async def expel_group_members(self, members: List[ID], group: ID) -> bool:
        """
        Expel members from this group

        :param members: members to be removed
        :param group:   group ID
        :return: True on success
        """
        assert group.is_group and len(members) > 0, 'params error: %s, %s' % (group, members)
        user = await self.facebook.current_user
        if user is None:
            return False
        else:
            delegate = self.delegate
        me = user.identifier
        old_members = await delegate.get_members(identifier=group)
        is_owner = await delegate.is_owner(user=me, group=group)
        is_admin = await delegate.is_administrator(user=me, group=group)
        # check permission
        can_reset = is_owner or is_admin
        if can_reset:
            # You are the owner/admin, then
            # remove the members and 'reset' the group
            new_members = old_members.copy()
            for item in members:
                remove_item(item=item, array=new_members)
            return await self.reset_group_members(members=new_members, group=group)
        # not an admin/owner
        raise PermissionError('Cannot expel members from group: %s' % group)

    async def invite_group_members(self, members: List[ID], group: ID) -> bool:
        """
        Invite new members to this group

        :param members: new members to be added
        :param group:   group ID
        :return: True on success
        """
        delegate = self.manager
        return await delegate.invite_members(members=members, group=group)

    async def quit_group(self, group: ID) -> bool:
        """ Quit from this group """
        delegate = self.manager
        return await delegate.quit_group(group=group)

    #
    #   Sending group message
    #

    async def send_instant_message(self, msg: InstantMessage, priority: int = 0) -> Optional[ReliableMessage]:
        """ Send group message """
        assert msg.content.group is not None, 'group message error: %s' % msg
        msg['GF'] = True  # group flag for notification
        delegate = self.emitter
        return await delegate.send_instant_message(msg=msg, priority=priority)


def remove_item(item, array: List):
    pos = len(array)
    while pos > 0:
        pos -= 1
        if array[pos] == item:
            array.pop(pos)
