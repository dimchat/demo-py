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
    2. only group owner or assistant can expel member
"""

from typing import List

from dimsdk import ID
from dimsdk import ReliableMessage
from dimsdk import Content
from dimsdk import ExpelCommand

from ...common import CommonFacebook

from .history import GroupCommandProcessor


class ExpelCommandProcessor(GroupCommandProcessor):

    @property
    def facebook(self) -> CommonFacebook:
        barrack = super().facebook
        assert isinstance(barrack, CommonFacebook), 'facebook error: %s' % barrack
        return barrack

    # Override
    def process_content(self, content: Content, r_msg: ReliableMessage) -> List[Content]:
        assert isinstance(content, ExpelCommand), 'expel command error: %s' % content
        facebook = self.facebook
        group = content.group
        owner = facebook.owner(identifier=group)
        members = facebook.members(identifier=group)
        # 0. check group
        if owner is None or len(members) == 0:
            return self._respond_receipt(text='Group empty.', msg=r_msg, group=group, extra={
                'template': 'Group empty: ${ID}',
                'replacements': {
                    'ID': str(group),
                }
            })
        # 1. check permission
        sender = r_msg.sender
        if sender != owner:
            # not the owner? check assistants
            assistants = facebook.assistants(identifier=group)
            if sender not in assistants:
                return self._respond_receipt(text='Permission denied.', msg=r_msg, group=group, extra={
                    'template': 'Not allowed to expel member from group: ${ID}',
                    'replacements': {
                        'ID': str(group),
                    }
                })
        # 2. expelling members
        expel_list = self.members(content=content)
        if len(expel_list) == 0:
            return self._respond_receipt(text='Command error.', msg=r_msg, group=group, extra={
                'template': 'Expel list is empty: ${ID}',
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
        # 2.2. build removed-list
        remove_list = []
        for item in expel_list:
            if item not in members:
                continue
            # expelled member found
            remove_list.append(item)
            members.remove(item)
        # 2.3. do expel
        if len(remove_list) > 0:
            man = group_manager()
            if man.save_members(members=members, group=group):
                content['removed'] = ID.revert(remove_list)
        # 3. response (no need to response this group command)
        return []


def group_manager():
    from ..group import GroupManager
    return GroupManager()
