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
    Expel Group Command Processor
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    1. remove group member(s)
    2. only group owner or administrator can expel member
"""

from typing import List, Tuple

from dimsdk import ID
from dimsdk import ReliableMessage
from dimsdk import Content
from dimsdk import ExpelCommand

from .history import GroupCommandProcessor


# Deprecated
class ExpelCommandProcessor(GroupCommandProcessor):

    # Override
    def process_content(self, content: Content, r_msg: ReliableMessage) -> List[Content]:
        assert isinstance(content, ExpelCommand), 'expel command error: %s' % content
        group = content.group
        # 0. check command
        if self._is_command_expired(command=content):
            # ignore expired command
            return []
        expel_list = self.command_members(content=content)
        if len(expel_list) == 0:
            return self._respond_receipt(text='Command error.', msg=r_msg, group=group, extra={
                'template': 'Expel list is empty: ${ID}',
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
        administrators = self.group_administrators(group=group)
        # 2. check permission
        sender = r_msg.sender
        if sender != owner and sender not in administrators:
            return self._respond_receipt(text='Permission denied.', msg=r_msg, group=group, extra={
                'template': 'Not allowed to expel member from group: ${ID}',
                'replacements': {
                    'ID': str(group),
                }
            })
        # 2.1. check owner
        if owner in expel_list:
            return self._respond_receipt(text='Permission denied.', msg=r_msg, group=group, extra={
                'template': 'Not allowed to expel owner of group: ${ID}',
                'replacements': {
                    'ID': str(group),
                }
            })
        # 2.2. check admins
        expel_admin = False
        for admin in administrators:
            if admin in expel_list:
                expel_admin = True
                break
        if expel_admin:
            return self._respond_receipt(text='Permission denied.', msg=r_msg, group=group, extra={
                'template': 'Not allowed to expel administrator of group: ${ID}',
                'replacements': {
                    'ID': str(group),
                }
            })
        # 3. do expel
        new_members, remove_list = calculate_expelled(members=members, expel_list=expel_list)
        if len(remove_list) > 0 and self.save_members(members=new_members, group=group):
            content['removed'] = ID.revert(array=remove_list)
        # no need to response this group command
        return []


def calculate_expelled(members: List[ID], expel_list: List[ID]) -> Tuple[List[ID], List[ID]]:
    new_members = []
    remove_list = []
    for item in members:
        if item in expel_list:
            # expelled member found
            remove_list.append(item)
        else:
            new_members.append(item)
    return new_members, remove_list
