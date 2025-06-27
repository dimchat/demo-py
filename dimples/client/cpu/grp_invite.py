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

from .group import GroupCommandProcessor


class InviteCommandProcessor(GroupCommandProcessor):

    # Override
    async def process_content(self, content: Content, r_msg: ReliableMessage) -> List[Content]:
        assert isinstance(content, InviteCommand), 'invite command error: %s' % content

        # 0. check command
        group, errors = await self._check_expired(content=content, r_msg=r_msg)
        if group is None:
            # ignore expired command
            return errors
        invite_list, errors = await self._check_command_members(content=content, r_msg=r_msg)
        if len(invite_list) == 0:
            # command error
            return errors

        # 1. check group
        trip = await self._check_group_members(content=content, r_msg=r_msg)
        owner = trip[0]
        members = trip[1]
        errors = trip[2]
        if owner is None or len(members) == 0:
            return errors

        sender = r_msg.sender
        admins = await self._administrators(group=group)
        is_owner = sender == owner
        is_admin = sender in admins
        is_member = sender in members
        can_reset = is_owner or is_admin
        cannot_reset = not can_reset

        # 2. check permission
        if not is_member:
            text = 'Permission denied.'
            return self._respond_receipt(text=text, content=content, envelope=r_msg.envelope, extra={
                'template': 'Not allowed to invite member into group: ${ID}',
                'replacements': {
                    'ID': str(group),
                }
            })

        # 3. do invite
        new_members, added_list = calculate_invited(members=members, invite_list=invite_list)
        if len(added_list) == 0:
            # maybe those users are already become members,
            # but if it can still receive an 'invite' command here,
            # we should respond the sender with the newest membership again.
            user = await self.facebook.current_user
            if cannot_reset and owner == user.identifier:
                # the sender cannot reset the group, means it's an ordinary member now,
                # and if I am the owner, then send the group history commands
                # to update the sender's memory.
                ok = await self.send_group_histories(group=group, receiver=sender)
                assert ok, 'failed to send history for group: %s => %s' % (group, sender)
        elif not await self._save_group_history(group=group, content=content, r_msg=r_msg):
            # here try to append the 'invite' command to local storage as group history
            # it should not failed unless the command is expired
            self.error(msg='failed to save "invite" command for group: %s' % group)
        elif cannot_reset:
            # the sender cannot reset the group, means it's invited by ordinary member,
            # and the 'invite' command was saved, now waiting for review.
            self.info(msg='"invite" command saved, waiting review now')
        elif await self._save_members(members=new_members, group=group):
            # FIXME: this sender has permission to reset the group,
            #        means it must be the owner or an administrator,
            #        usually it should send a 'reset' command instead;
            #        if we received the 'invite' command here, maybe it was confused,
            #        anyway, we just append the new members directly.
            self.warning(msg='invited by administrator: %s, group: %s' % (sender, group))
            content['added'] = ID.revert(identifiers=added_list)
        else:
            # DB error?
            assert False, 'failed to save members for group: %s' % group

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
