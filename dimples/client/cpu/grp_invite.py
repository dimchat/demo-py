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
    Invite Group Command Processor
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    1. add new member(s) to the group
    2. any member can invite new member
    3. invited by ordinary member should be reviewed by owner/administrator
"""

from typing import Optional, List

from dimsdk import ID
from dimsdk import ReliableMessage
from dimsdk import Content
from dimsdk import InviteCommand

from .history import GroupCommandProcessor


class InviteCommandProcessor(GroupCommandProcessor):

    # Override
    def process_content(self, content: Content, r_msg: ReliableMessage) -> List[Content]:
        assert isinstance(content, InviteCommand), 'invite command error: %s' % content
        group = content.group
        # 0. check command
        invite_list = self.command_members(content=content)
        if len(invite_list) == 0:
            return self._respond_receipt(text='Command error.', msg=r_msg, group=group, extra={
                'template': 'Invite list is empty: ${ID}',
                'replacements': {
                    'ID': str(group),
                }
            })
        # 1. check group
        owner = self.group_owner(group=group)
        members = self.group_members(group=group)
        if owner is None or len(members) == 0:
            return self._respond_receipt(text='Group empty.', msg=r_msg, group=group, extra={
                'template': 'Group empty: ${ID}',
                'replacements': {
                    'ID': str(group),
                }
            })
        # 2. check permission
        sender = r_msg.sender
        if sender not in members:
            return self._respond_receipt(text='Permission denied.', msg=r_msg, group=group, extra={
                'template': 'Not allowed to invite member into group: ${ID}',
                'replacements': {
                    'ID': str(group),
                }
            })
        administrators = self.group_administrators(group=group)
        # 3. do invite
        if sender == owner or sender in administrators:
            # invite by owner or admin, so
            # append them directly.
            added_list = self.__append_members(group=group, members=members, invite_list=invite_list)
            if added_list is not None:
                content['added'] = ID.revert(array=added_list)
        else:
            # add an invitation in bulletin for reviewing
            self._add_invitation(content=content)
        # no need to response this group command
        return []

    def __append_members(self, group: ID, members: List[ID], invite_list: List[ID]) -> Optional[List[ID]]:
        added_list = []
        for item in invite_list:
            if item not in members:
                members.append(item)
                added_list.append(item)
        if len(added_list) == 0:
            # nothing changed
            return None
        if self.save_members(members=members, group=group):
            return added_list
        assert False, 'failed to save members in group: %s, %s' % (group, members)
