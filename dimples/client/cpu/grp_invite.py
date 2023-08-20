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
    2. any member or assistant can invite new member
"""

from typing import List

from dimsdk import ID
from dimsdk import ReliableMessage
from dimsdk import Content
from dimsdk import InviteCommand

from ...common import CommonFacebook

from .grp_reset import ResetCommandProcessor


class InviteCommandProcessor(ResetCommandProcessor):

    @property
    def facebook(self) -> CommonFacebook:
        barrack = super().facebook
        assert isinstance(barrack, CommonFacebook), 'facebook error: %s' % barrack
        return barrack

    # Override
    def process_content(self, content: Content, r_msg: ReliableMessage) -> List[Content]:
        assert isinstance(content, InviteCommand), 'invite command error: %s' % content
        facebook = self.facebook
        group = content.group
        owner = facebook.owner(identifier=group)
        members = facebook.members(identifier=group)
        # 0. check group
        if owner is None or len(members) == 0:
            # NOTICE: group membership lost?
            #         reset group members
            return self._temporary_save(content=content, sender=r_msg.sender, msg=r_msg)
        # 1. check permission
        sender = r_msg.sender
        if sender not in members:
            # not a member? check assistants
            assistants = facebook.assistants(identifier=group)
            if sender not in assistants:
                return self._respond_receipt(text='Permission denied.', msg=r_msg, group=group, extra={
                    'template': 'Not allowed to invite member into group: ${ID}',
                    'replacements': {
                        'ID': str(group),
                    }
                })
        # 2. inviting members
        invite_list = self.members(content=content)
        if len(invite_list) == 0:
            return self._respond_receipt(text='Command error.', msg=r_msg, group=group, extra={
                'template': 'Invite list is empty: ${ID}',
                'replacements': {
                    'ID': str(group),
                }
            })
        # 2.1. check for reset
        if sender == owner and owner in invite_list:
            # NOTICE: owner invites owner?
            #         it means this should be a 'reset' command
            return self._temporary_save(content=content, sender=sender, msg=r_msg)
        # 2.2. build invited-list
        add_list = []
        for item in invite_list:
            if item in members:
                continue
            # new member found
            add_list.append(item)
            members.append(item)
        # 2.3. do invite
        if len(add_list) > 0:
            man = group_manager()
            if man.save_members(members=members, group=group):
                content['added'] = ID.revert(add_list)
        # 3. response (no need to response this group command)
        return []


def group_manager():
    from ..group import GroupManager
    return GroupManager()
