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
    Quit Group Command Processor
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    1. remove the sender from members of the group
    2. owner and administrator cannot quit
"""

from typing import List

from dimsdk import ReliableMessage
from dimsdk import Content
from dimsdk import QuitCommand

from .group import GroupCommandProcessor


class QuitCommandProcessor(GroupCommandProcessor):

    # Override
    async def process_content(self, content: Content, r_msg: ReliableMessage) -> List[Content]:
        assert isinstance(content, QuitCommand), 'quit command error: %s' % content

        # 0. check command
        group, errors = await self._check_expired(content=content, r_msg=r_msg)
        if group is None:
            # ignore expired command
            return errors

        # 1. check group
        owner, members, errors = await self._check_group_members(content=content, r_msg=r_msg)
        if owner is None or len(members) == 0:
            return errors

        sender = r_msg.sender
        admins = await self._administrators(group=group)
        is_owner = sender == owner
        is_admin = sender in admins
        is_member = sender in members

        # 2. check permission
        if is_owner:
            text = 'Permission denied.'
            return self._respond_receipt(text=text, content=content, envelope=r_msg.envelope, extra={
                'template': 'Owner cannot quit from group: ${ID}',
                'replacements': {
                    'ID': str(group),
                }
            })
        if is_admin:
            text = 'Permission denied.'
            return self._respond_receipt(text=text, content=content, envelope=r_msg.envelope, extra={
                'template': 'Administrator cannot quit from group: ${ID}',
                'replacements': {
                    'ID': str(group),
                }
            })
        if is_member:
            new_members = members.copy()
            new_members.remove(sender)
            members = new_members

        # 3. do quit
        if not is_member:
            # the sender is not a member now,
            # shall we notify the sender that the member list was updated?
            self.warning(msg='not a member now: %s, %s' % (sender, group))
        elif not await self._save_group_history(group=group, content=content, r_msg=r_msg):
            # here try to append the 'quit' command to local storage as group history
            # it should not failed unless the command is expired
            self.error(msg='failed to save "quit" command for group: %s' % group)
        elif await self._save_members(members=members, group=group):
            # here try to remove the sender from member list
            content['removed'] = [str(sender)]
        else:
            # DB error?
            assert False, 'failed to save members for group: %s' % group

        # no need to response this group command
        return []
