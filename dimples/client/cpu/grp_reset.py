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
    Reset Group Command Processor
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    1. reset group members
    2. only group owner or assistant can reset group members
"""

from typing import Tuple, List

from dimsdk import ID
from dimsdk import ReliableMessage
from dimsdk import Content
from dimsdk import ResetCommand

from .group import GroupCommandProcessor


class ResetCommandProcessor(GroupCommandProcessor):

    # Override
    def process_content(self, content: Content, r_msg: ReliableMessage) -> List[Content]:
        assert isinstance(content, ResetCommand), 'group cmd error: %s' % content

        # 0. check command
        pair = self._check_expired(content=content, r_msg=r_msg)
        group = pair[0]
        errors = pair[1]
        if group is None:
            # ignore expired command
            return errors
        pair = self._check_command_members(content=content, r_msg=r_msg)
        new_members = pair[0]
        errors = pair[1]
        if len(new_members) == 0:
            # command error
            return errors

        # 1. check group
        trip = self._check_group_members(content=content, r_msg=r_msg)
        owner = trip[0]
        members = trip[1]
        errors = trip[2]
        if owner is None or len(members) == 0:
            return errors

        sender = r_msg.sender
        administrators = self._administrators(group=group)
        is_owner = sender == owner
        is_admin = sender in administrators
        can_reset = is_owner or is_admin
        cannot_reset = not can_reset

        # 2. check permission
        if cannot_reset:
            text = 'Permission denied.'
            return self._respond_receipt(text=text, content=content, envelope=r_msg.envelope, extra={
                'template': 'Not allowed to reset members of group: ${ID}',
                'replacements': {
                    'ID': str(group),
                }
            })
        # 2.1. check owner
        if owner != new_members[0]:
            text = 'Permission denied.'
            return self._respond_receipt(text=text, content=content, envelope=r_msg.envelope, extra={
                'template': 'Owner must be the first member of group: ${ID}',
                'replacements': {
                    'ID': str(group),
                }
            })
        # 2.2. check admins
        expel_admin = False
        for admin in administrators:
            if admin not in new_members:
                expel_admin = True
                break
        if expel_admin:
            text = 'Permission denied.'
            return self._respond_receipt(text=text, content=content, envelope=r_msg.envelope, extra={
                'template': 'Not allowed to expel administrator of group: ${ID}',
                'replacements': {
                    'ID': str(group),
                }
            })

        # 3. do reset
        pair = calculate_reset(old_members=members, new_members=new_members)
        add_list = pair[0]
        remove_list = pair[1]
        if not self._save_group_history(group=group, content=content, r_msg=r_msg):
            # here try to save the 'reset' command to local storage as group history
            # it should not failed unless the command is expired
            self.error(msg='failed to save "reset" command for group: %s' % group)
        elif len(add_list) == 0 and len(remove_list) == 0:
            # nothing changed
            self.warning(msg='nothing changed for group members: %d, %s' % (len(members), group))
        elif self._save_members(members=new_members, group=group):
            self.info(msg='new members saved in group: %s' % group)
            if len(add_list) > 0:
                content['added'] = ID.revert(add_list)
            if len(remove_list) > 0:
                content['removed'] = ID.revert(remove_list)
        else:
            # DB error?
            assert False, 'failed to save members for group: %s' % group

        # no need to response this group command
        return []


def calculate_reset(old_members: List[ID], new_members: List[ID]) -> Tuple[List[ID], List[ID]]:
    add_list = []
    remove_list = []
    # build invited-list
    for item in new_members:
        if item not in old_members:
            add_list.append(item)
    # build expelled-list
    for item in old_members:
        if item not in new_members:
            remove_list.append(item)
    return add_list, remove_list
