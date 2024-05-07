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
from typing import Dict, List

from dimsdk import ID
from dimsdk import FrequencyChecker
from dimsdk import Document
from dimsdk import MetaCommand, DocumentCommand, GroupCommand, QueryCommand
from dimsdk import Station

from ..common import AccountDBI
from ..common import CommonArchivist
from ..common import CommonMessenger


def get_facebook(archivist: CommonArchivist):
    facebook = archivist.facebook
    if facebook is not None:
        from .facebook import ClientFacebook
        assert isinstance(facebook, ClientFacebook), 'facebook error: %s' % facebook
    return facebook


def get_messenger(archivist: CommonArchivist):
    messenger = archivist.messenger
    if messenger is not None:
        assert isinstance(messenger, CommonMessenger), 'messenger error: %s' % messenger
    return messenger


class ClientArchivist(CommonArchivist, ABC):

    # each respond will be expired after 10 minutes
    RESPOND_EXPIRES = 600.0  # seconds

    def __init__(self, database: AccountDBI):
        super().__init__(database=database)
        self.__document_responses = FrequencyChecker(expires=self.RESPOND_EXPIRES)
        self.__last_active_members: Dict[ID, ID] = {}  # group => member

    # protected
    def is_documents_respond_expired(self, identifier: ID, force: bool) -> bool:
        return self.__document_responses.is_expired(key=identifier, force=force)

    def set_last_active_member(self, member: ID, group: ID):
        self.__last_active_members[group] = member

    # Override
    async def query_meta(self, identifier: ID) -> bool:
        if not self.is_meta_query_expired(identifier=identifier):
            # query not expired yet
            self.info(msg='meta query not expired yet: %s' % identifier)
            return False
        messenger = get_messenger(archivist=self)
        if messenger is None:
            self.warning(msg='messenger not ready yet')
            return False
        self.info(msg='querying meta for: %s' % identifier)
        command = MetaCommand.query(identifier=identifier)
        _, r_msg = await messenger.send_content(sender=None, receiver=Station.ANY, content=command, priority=1)
        return r_msg is not None

    # Override
    async def query_documents(self, identifier: ID, documents: List[Document]) -> bool:
        if not self.is_documents_query_expired(identifier=identifier):
            # query not expired yet
            self.info(msg='document query not expired yet: %s' % identifier)
            return False
        messenger = get_messenger(archivist=self)
        if messenger is None:
            self.warning(msg='messenger not ready yet')
            return False
        last_time = await self.get_last_document_time(identifier=identifier, documents=documents)
        self.info(msg='querying document for: %s, last time: %s' % (identifier, last_time))
        command = DocumentCommand.query(identifier=identifier, last_time=last_time)
        _, r_msg = await messenger.send_content(sender=None, receiver=Station.ANY, content=command, priority=1)
        return r_msg is not None

    # Override
    async def query_members(self, group: ID, members: List[ID]) -> bool:
        if not self.is_members_query_expired(group=group):
            # query not expired yet
            self.info('members query not expired yet: %s' % group)
            return False
        facebook = get_facebook(archivist=self)
        messenger = get_messenger(archivist=self)
        if facebook is None or messenger is None:
            self.warning(msg='facebook messenger not ready yet')
            return False
        user = facebook.current_user
        if user is None:
            self.error(msg='failed to get current user')
            return False
        me = user.identifier
        last_time = await self.get_last_group_history_time(group=group)
        self.info(msg='querying members for group: %s, last time: %s' % (group, last_time))
        # build query command for group members
        command = GroupCommand.query(group=group, last_time=last_time)
        # 1. check group bots
        ok = await self.query_members_from_assistants(command=command, sender=me, group=group)
        if ok:
            return True
        # 2. check administrators
        ok = await self.query_members_from_administrators(command=command, sender=me, group=group)
        if ok:
            return True
        # 3. check group owner
        ok = await self.query_members_from_owner(command=command, sender=me, group=group)
        if ok:
            return True
        # all failed, try last active member
        last_member = self.__last_active_members.get(group)
        if last_member is None:
            r_msg = None
        else:
            self.info(msg='querying members from: %s, group: %s' % (last_member, group))
            _, r_msg = await messenger.send_content(sender=me, receiver=last_member, content=command, priority=1)
        self.error(msg='group not ready: %s' % group)
        return r_msg is not None

    # protected
    async def query_members_from_assistants(self, command: QueryCommand, sender: ID, group: ID) -> bool:
        facebook = get_facebook(archivist=self)
        messenger = get_messenger(archivist=self)
        if facebook is None or messenger is None:
            self.warning(msg='facebook messenger not ready yet')
            return False
        bots = await facebook.get_assistants(group)
        if len(bots) == 0:
            self.warning(msg='assistants not designated for group: %s' % group)
            return False
        success = 0
        # querying members from bots
        self.info(msg='querying members from bots: %s, group: %s' % (bots, group))
        for receiver in bots:
            if receiver == sender:
                self.warning(msg='ignore cycled querying: %s, group: %s' % (receiver, group))
                continue
            _, r_msg = await messenger.send_content(sender=sender, receiver=receiver, content=command, priority=1)
            if r_msg is not None:
                success += 1
        if success == 0:
            # failed
            return False
        last_member = self.__last_active_members.get(group)
        if last_member is None or last_member in bots:
            # last active member is a bot??
            pass
        else:
            self.info(msg='querying members from: %s, group: %s' % (last_member, group))
            await messenger.send_content(sender=sender, receiver=last_member, content=command, priority=1)
        return True

    # protected
    async def query_members_from_administrators(self, command: QueryCommand, sender: ID, group: ID) -> bool:
        facebook = get_facebook(archivist=self)
        messenger = get_messenger(archivist=self)
        if facebook is None or messenger is None:
            self.warning(msg='facebook messenger not ready yet')
            return False
        admins = await facebook.get_administrators(group)
        if len(admins) == 0:
            self.warning(msg='administrators not found for group: %s' % group)
            return False
        success = 0
        # querying members from admins
        self.info(msg='querying members from admins: %s, group: %s' % (admins, group))
        for receiver in admins:
            if receiver == sender:
                self.warning(msg='ignore cycled querying: %s, group: %s' % (receiver, group))
                continue
            _, r_msg = await messenger.send_content(sender=sender, receiver=receiver, content=command, priority=1)
            if r_msg is not None:
                success += 1
        if success == 0:
            # failed
            return False
        last_member = self.__last_active_members.get(group)
        if last_member is None or last_member in admins:
            # last active member is an admin, already queried
            pass
        else:
            self.info(msg='querying members from: %s, group: %s' % (last_member, group))
            await messenger.send_content(sender=sender, receiver=last_member, content=command, priority=1)
        return True

    # protected
    async def query_members_from_owner(self, command: QueryCommand, sender: ID, group: ID) -> bool:
        facebook = get_facebook(archivist=self)
        messenger = get_messenger(archivist=self)
        if facebook is None or messenger is None:
            self.warning(msg='facebook messenger not ready yet')
            return False
        owner = await facebook.get_owner(group)
        if owner is None:
            self.warning(msg='owner not found for group: %s' % group)
            return False
        elif owner == sender:
            self.error(msg='you are the owner of group: %s' % group)
            return False
        # querying members from owner
        self.info(msg='querying members from owner: %s, group: %s' % (owner, group))
        _, r_msg = await messenger.send_content(sender=sender, receiver=owner, content=command, priority=1)
        if r_msg is None:
            # failed
            return False
        last_member = self.__last_active_members.get(group)
        if last_member is None or last_member == owner:
            # last active member is the owner, already queried
            pass
        else:
            self.info(msg='querying members from: %s, group: %s' % (last_member, group))
            await messenger.send_content(sender=sender, receiver=last_member, content=command, priority=1)
        return True
