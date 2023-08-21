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

"""
    Group History Processors
    ~~~~~~~~~~~~~~~~~~~~~~~~

"""

from typing import Optional, Union, List

from dimsdk import ID, Bulletin
from dimsdk import ReliableMessage
from dimsdk import Content, ForwardContent
from dimsdk import Command, GroupCommand
from dimsdk import InviteCommand, JoinCommand
from dimsdk import BaseCommandProcessor

from ...common import CommonFacebook, CommonMessenger


class HistoryCommandProcessor(BaseCommandProcessor):

    # Override
    def process_content(self, content: Content, r_msg: ReliableMessage) -> List[Content]:
        assert isinstance(content, Command), 'history command error: %s' % content
        return self._respond_receipt(text='Command not support.', msg=r_msg, group=content.group, extra={
            'template': 'History command (name: ${command}) not support yet!',
            'replacements': {
                'command': content.cmd,
            }
        })


class GroupCommandProcessor(HistoryCommandProcessor):

    @property
    def messenger(self) -> CommonMessenger:
        transceiver = super().messenger
        assert isinstance(transceiver, CommonMessenger), 'messenger error: %s' % transceiver
        return transceiver

    @property
    def facebook(self) -> CommonFacebook:
        barrack = super().facebook
        assert isinstance(barrack, CommonFacebook), 'facebook error: %s' % barrack
        return barrack

    def group_owner(self, group: ID) -> Optional[ID]:
        facebook = self.facebook
        return facebook.owner(identifier=group)

    def group_members(self, group: ID) -> List[ID]:
        facebook = self.facebook
        return facebook.members(identifier=group)

    def group_assistants(self, group: ID) -> List[ID]:
        facebook = self.facebook
        return facebook.assistants(identifier=group)

    def group_administrators(self, group: ID) -> List[ID]:
        db = self.facebook.database
        return db.administrators(group=group)

    def save_members(self, members: List[ID], group: ID) -> bool:
        db = self.facebook.database
        return db.save_members(members=members, group=group)

    def save_administrators(self, administrators: List[ID], group: ID) -> bool:
        db = self.facebook.database
        return db.save_administrators(administrators=administrators, group=group)

    @staticmethod
    def command_members(content: GroupCommand) -> List[ID]:
        # get from 'members'
        array = content.members
        if array is None:
            # get from 'member
            item = content.member
            if item is None:
                array = []
            else:
                array = [item]
        return array

    # Override
    def process_content(self, content: Content, r_msg: ReliableMessage) -> List[Content]:
        assert isinstance(content, GroupCommand), 'group command error: %s' % content
        return self._respond_receipt(text='Command not support.', msg=r_msg, group=content.group, extra={
            'template': 'Group command (name: ${command}) not support yet!',
            'replacements': {
                'command': content.cmd,
            }
        })

    def _add_invitation(self, content: Union[InviteCommand, JoinCommand]):
        """ add 'invite', 'join' commands to bulletin.invitations for owner/admins to review """
        group = content.group
        owner = self.group_owner(group=group)
        administrators = self.group_administrators(group=group)
        user = self.facebook.current_user
        if user.identifier != owner and user.identifier not in administrators:
            # only add invitation for owner/admin
            return False
        bulletin = self.facebook.document(identifier=group)
        assert isinstance(bulletin, Bulletin), 'group document error: %s, %s' % (group, bulletin)
        invitations = bulletin.get('invitations')
        if isinstance(invitations, List):
            invitations.append(content.dictionary)
        else:
            bulletin['invitations'] = [content.dictionary]
        return self.facebook.save_document(document=bulletin)

    def _send_reset_command(self, group: ID, members: List[ID], receiver: ID):
        """ send a reset command with newest members to the receiver """
        owner = self.group_owner(group=group)
        administrators = self.group_administrators(group=group)
        user = self.facebook.current_user
        if user.identifier == owner or user.identifier in administrators:
            # this is the group owner (or administrator), so
            # it has permission to reset group members here.
            content = GroupCommand.reset(group=group, members=members)
        else:
            # this is a group bot, it has no permission to change group members,
            # try to load reset command from database which sent by the owner or an administrator
            db = self.facebook.database
            _, msg = db.reset_command_message(group=group)
            if msg is None:
                return False
            content = ForwardContent.create(message=msg)
        self.messenger.send_content(sender=user.identifier, receiver=receiver, content=content, priority=1)
        return True
