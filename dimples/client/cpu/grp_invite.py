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

from typing import List, Tuple

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
        if self._is_command_expired(command=content):
            # ignore expired command
            return []
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
            # TODO: query group members?
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
        new_members, added_list = calculate_invited(members=members, invite_list=invite_list)
        if sender == owner or sender in administrators:
            # invite by owner or admin, so
            # append them directly.
            if len(added_list) > 0 and self.save_members(members=new_members, group=group):
                content['added'] = ID.revert(array=added_list)
        else:
            if len(added_list) == 0:
                # maybe the invited users are already become members,
                # but if it can still receive a join command here,
                # we should respond the sender with the newest membership again.
                self._send_reset_command(group=group, members=new_members, receiver=sender)
            else:
                # add 'invite' application for waiting review
                self._add_application(command=content, message=r_msg)
        # no need to response this group command
        return []


def calculate_invited(members: List[ID], invite_list: List[ID]) -> Tuple[List[ID], List[ID]]:
    new_members = members.copy()
    added_list = []
    for item in invite_list:
        if item not in new_members:
            new_members.append(item)
            added_list.append(item)
    return new_members, added_list
