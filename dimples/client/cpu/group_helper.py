# -*- coding: utf-8 -*-
#
#   DIM-SDK : Decentralized Instant Messaging Software Development Kit
#
#                                Written in 2019 by Moky <albert.moky@gmail.com>
#
# ==============================================================================
# MIT License
#
# Copyright (c) 2019 Albert Moky
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

from typing import Optional, Tuple, List

from dimsdk import ID, Meta, Document
from dimsdk import ReliableMessage
from dimsdk import GroupCommand, ResetCommand, ResignCommand
from dimsdk import TwinsHelper

from ...utils import Logging
from ...utils import is_before
from ...common import CommonFacebook, CommonMessenger


class GroupCommandHelper(TwinsHelper, Logging):

    @property
    def facebook(self) -> CommonFacebook:
        barrack = super().facebook
        assert isinstance(barrack, CommonFacebook), 'barrack error: %s' % barrack
        return barrack

    @property
    def messenger(self) -> CommonMessenger:
        transceiver = super().messenger
        assert isinstance(transceiver, CommonMessenger), 'transceiver error: %s' % transceiver
        return transceiver

    def meta(self, group: ID) -> Optional[Meta]:
        """ get group meta
            if not found, query it from any station
        """
        info = self.facebook.meta(identifier=group)
        if info is None:
            self.messenger.query_meta(identifier=group)
        return info

    def document(self, group: ID) -> Optional[Document]:
        """ get group document
            if not found, query it from any station
        """
        info = self.facebook.document(identifier=group)
        if info is None:
            self.messenger.query_document(identifier=group)
        return info

    def owner(self, group: ID) -> Optional[ID]:
        """ get group owner
            when bulletin document exists
        """
        doc = self.document(group=group)
        if doc is None:
            # the owner(founder) should be set in the bulletin document of group
            return None
        return self.facebook.owner(identifier=group)

    def assistants(self, group: ID) -> List[ID]:
        """ get group bots
            when bulletin document exists
        """
        doc = self.document(group=group)
        if doc is None:
            # the group bots should be set in the bulletin document of group
            return []
        return self.facebook.assistants(identifier=group)

    def administrators(self, group: ID) -> List[ID]:
        """ get administrators
            when bulletin document exists
        """
        doc = self.document(group=group)
        if doc is None:
            # the administrators should be set in the bulletin document of group
            return []
        db = self.facebook.database
        return db.administrators(group=group)

    def save_administrators(self, administrators: List[ID], group: ID) -> bool:
        db = self.facebook.database
        return db.save_administrators(administrators=administrators, group=group)

    def members(self, group: ID) -> List[ID]:
        """ get members when owner exists,
            if not found, query from bots/admins/owner
        """
        owner = self.owner(group=group)
        if owner is None:
            # the owner must exists before members
            return []
        users = self.facebook.members(identifier=group)
        if len(users) == 0:
            self.messenger.query_members(identifier=group)
        return users

    def save_members(self, members: List[ID], group: ID) -> bool:
        db = self.facebook.database
        return db.save_members(members=members, group=group)

    #
    #   Group History Command
    #

    def save_group_history(self, group: ID, content: GroupCommand, message: ReliableMessage) -> bool:
        if self.is_expired(content=content):
            self.warning(msg='drop expired command: %s, %s => %s' % (content.cmd, message.sender, group))
            return False
        db = self.facebook.database
        if isinstance(content, ResetCommand):
            self.warning(msg='cleaning group history for "reset" command: %s => %s' % (message.sender, group))
            db.clear_group_member_histories(group=group)
        return db.save_group_history(group=group, content=content, message=message)

    def group_histories(self, group: ID) -> List[Tuple[GroupCommand, ReliableMessage]]:
        db = self.facebook.database
        return db.group_histories(group=group)

    def reset_command_message(self, group: ID) -> Tuple[Optional[ResetCommand], Optional[ReliableMessage]]:
        db = self.facebook.database
        return db.reset_command_message(group=group)

    def clear_group_member_histories(self, group: ID) -> bool:
        db = self.facebook.database
        return db.clear_group_member_histories(group=group)

    def clear_group_admin_histories(self, group: ID) -> bool:
        db = self.facebook.database
        return db.clear_group_admin_histories(group=group)

    def is_expired(self, content: GroupCommand) -> bool:
        """ check command time
            (all group commands received must after the cached 'reset' command)
        """
        group = content.group
        assert group is not None, 'group content error: %s' % content
        if isinstance(content, ResignCommand):
            # administrator command, check with document time
            doc = self.document(group=group)
            if doc is None:
                self.error(msg='group document not exists: %s' % group)
                return True
            return is_before(old_time=doc.time, new_time=content.time)
        # membership command, check with reset command
        pair = self.reset_command_message(group=group)
        cmd = pair[0]
        # msg = pair[1]
        if cmd is None:  # or msg is None:
            return False
        return is_before(old_time=cmd.time, new_time=content.time)

    # noinspection PyMethodMayBeStatic
    def members_from_command(self, content: GroupCommand) -> List[ID]:
        # get from 'members'
        members = content.members
        if members is None:
            # get from 'member
            single = content.member
            members = [] if single is None else [single]
        return members
