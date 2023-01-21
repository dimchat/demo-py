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

from dimp import ID
from dimp import ReliableMessage
from dimp import Content
from dimp import InviteCommand

from .grp_reset import ResetCommandProcessor


class InviteCommandProcessor(ResetCommandProcessor):

    STR_INVITE_CMD_ERROR = 'Invite command error.'
    STR_INVITE_NOT_ALLOWED = 'Sorry, you are not allowed to invite new members into this group.'

    # Override
    def process(self, content: Content, msg: ReliableMessage) -> List[Content]:
        assert isinstance(content, InviteCommand), 'invite command error: %s' % content
        facebook = self.facebook
        group = content.group
        owner = facebook.owner(identifier=group)
        members = facebook.members(identifier=group)
        # 0. check group
        if owner is None or members is None or len(members) == 0:
            # NOTICE: group membership lost?
            #         reset group members
            return self._temporary_save(content=content, sender=msg.sender)
        # 1. check permission
        sender = msg.sender
        if sender not in members:
            # not a member? check assistants
            assistants = facebook.assistants(identifier=group)
            if assistants is None or sender not in assistants:
                text = self.STR_INVITE_NOT_ALLOWED
                return self._respond_text(text=text, group=group)
        # 2. inviting members
        invite_list = self.members(content=content)
        if invite_list is None or len(invite_list) == 0:
            text = self.STR_INVITE_CMD_ERROR
            return self._respond_text(text=text, group=group)
        # 2.1. check for reset
        if sender == owner and owner in invite_list:
            # NOTICE: owner invites owner?
            #         it means this should be a 'reset' command
            return self._temporary_save(content=content, sender=sender)
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
            if facebook.save_members(members=members, identifier=group):
                content['added'] = ID.revert(add_list)
        # 3. response (no need to response this group command)
        return []
