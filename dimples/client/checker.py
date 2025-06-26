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
from typing import Optional, List

from dimsdk import ID, Document, Visa
from dimsdk import MetaCommand, DocumentCommand
from dimsdk import GroupCommand, QueryCommand
from dimsdk import Station

from ..utils import Logging
from ..common import EntityChecker
from ..common import AccountDBI
from ..common import CommonFacebook, CommonMessenger


class ClientChecker(EntityChecker, Logging):

    def __init__(self, database: AccountDBI, facebook: CommonFacebook):
        super().__init__(database=database)
        self.__barrack = weakref.ref(facebook)
        self.__transceiver = None

    @property
    def facebook(self) -> Optional[CommonFacebook]:
        return self.__barrack()

    @property
    def messenger(self) -> Optional[CommonMessenger]:
        ref = self.__transceiver
        if ref is not None:
            return ref()

    @messenger.setter
    def messenger(self, transceiver: CommonMessenger):
        self.__transceiver = None if transceiver is None else weakref.ref(transceiver)

    # Override
    async def query_meta(self, identifier: ID) -> bool:
        messenger = self.messenger
        if messenger is None:
            self.error(msg='messenger not ready yet')
            return False
        elif not self.is_meta_query_expired(identifier=identifier):
            # query not expired yet
            self.debug(msg='meta query not expired yet: %s' % identifier)
            return False
        self.info(msg='querying meta for: %s' % identifier)
        content = MetaCommand.query(identifier=identifier)
        _, r_msg = await messenger.send_content(content=content, sender=None, receiver=Station.ANY, priority=1)
        return r_msg is not None

    # Override
    async def query_documents(self, identifier: ID, documents: List[Document]) -> bool:
        messenger = self.messenger
        if messenger is None:
            self.error(msg='messenger not ready yet')
            return False
        elif not self.is_document_query_expired(identifier=identifier):
            # query not expired yet
            self.debug(msg='document query not expired yet: %s' % identifier)
            return False
        last_time = self.get_last_document_time(identifier=identifier, documents=documents)
        self.info(msg='querying document for: %s, last time: %s' % (identifier, last_time))
        content = DocumentCommand.query(identifier=identifier, last_time=last_time)
        _, r_msg = await messenger.send_content(content=content, sender=None, receiver=Station.ANY, priority=1)
        return r_msg is not None

    # Override
    async def query_members(self, group: ID, members: List[ID]) -> bool:
        facebook = self.facebook
        messenger = self.messenger
        if facebook is None or messenger is None:
            self.error(msg='facebook messenger not ready yet')
            return False
        elif not self.is_members_query_expired(identifier=group):
            # query not expired yet
            self.debug('members query not expired yet: %s' % group)
            return False
        user = await facebook.current_user
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
        last_member = self.get_last_active_member(group=group)
        if last_member is None:
            r_msg = None
        else:
            self.info(msg='querying members from: %s, group: %s' % (last_member, group))
            _, r_msg = await messenger.send_content(sender=me, receiver=last_member, content=command, priority=1)
        self.error(msg='group not ready: %s' % group)
        return r_msg is not None

    # protected
    async def query_members_from_assistants(self, command: QueryCommand, sender: ID, group: ID) -> bool:
        facebook = self.facebook
        messenger = self.messenger
        if facebook is None or messenger is None:
            self.error(msg='facebook messenger not ready yet')
            return False
        bots = await facebook.get_assistants(group)
        if bots is None or len(bots) == 0:
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
        last_member = self.get_last_active_member(group=group)
        if last_member is None or last_member in bots:
            # last active member is a bot??
            pass
        else:
            self.info(msg='querying members from: %s, group: %s' % (last_member, group))
            await messenger.send_content(sender=sender, receiver=last_member, content=command, priority=1)
        return True

    # protected
    async def query_members_from_administrators(self, command: QueryCommand, sender: ID, group: ID) -> bool:
        facebook = self.facebook
        messenger = self.messenger
        if facebook is None or messenger is None:
            self.error(msg='facebook messenger not ready yet')
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
        last_member = self.get_last_active_member(group=group)
        if last_member is None or last_member in admins:
            # last active member is an admin, already queried
            pass
        else:
            self.info(msg='querying members from: %s, group: %s' % (last_member, group))
            await messenger.send_content(sender=sender, receiver=last_member, content=command, priority=1)
        return True

    # protected
    async def query_members_from_owner(self, command: QueryCommand, sender: ID, group: ID) -> bool:
        facebook = self.facebook
        messenger = self.messenger
        if facebook is None or messenger is None:
            self.error(msg='facebook messenger not ready yet')
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
        last_member = self.get_last_active_member(group=group)
        if last_member is None or last_member == owner:
            # last active member is the owner, already queried
            pass
        else:
            self.info(msg='querying members from: %s, group: %s' % (last_member, group))
            await messenger.send_content(sender=sender, receiver=last_member, content=command, priority=1)
        return True

    # Override
    async def send_visa(self, visa: Visa, receiver: ID, updated: bool = False) -> bool:
        me = visa.identifier
        if me == receiver:
            self.warning(msg='skip cycled message: %s, %s' % (receiver, visa))
            return False
        messenger = self.messenger
        if messenger is None:
            self.error(msg='messenger not ready yet')
            return False
        elif not self.is_document_response_expired(identifier=receiver, force=updated):
            # response not expired yet
            self.debug(msg='visa response not expired yet: %s' % receiver)
            return False
        self.info(msg='push visa document: %s => %s' % (me, receiver))
        content = DocumentCommand.response(identifier=me, meta=None, documents=[visa])
        _, r_msg = await messenger.send_content(content=content, sender=me, receiver=receiver, priority=1)
        return r_msg is not None
