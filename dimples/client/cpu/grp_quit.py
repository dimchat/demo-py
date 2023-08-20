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

    1. quit the group
    2. owner and assistant cannot quit
    3. assistant can be hired/fired by owner
"""

from typing import List

from dimsdk import ID
from dimsdk import ReliableMessage
from dimsdk import Content
from dimsdk import QuitCommand

from ...common import CommonFacebook

from .history import GroupCommandProcessor


class QuitCommandProcessor(GroupCommandProcessor):

    @property
    def facebook(self) -> CommonFacebook:
        barrack = super().facebook
        assert isinstance(barrack, CommonFacebook), 'facebook error: %s' % barrack
        return barrack

    # noinspection PyUnusedLocal
    def _remove_assistant(self, content: QuitCommand, sender: ID, msg: ReliableMessage) -> List[Content]:
        # NOTICE: group assistant should be retired by the owner
        group = content.group
        return self._respond_receipt(text='Permission denied.', msg=msg, group=group, extra={
            'template': 'Assistant cannot quit from group: ${ID}',
            'replacements': {
                'ID': str(group),
            }
        })

    # Override
    def process_content(self, content: Content, r_msg: ReliableMessage) -> List[Content]:
        assert isinstance(content, QuitCommand), 'quit command error: %s' % content
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
        if sender == owner:
            return self._respond_receipt(text='Permission denied.', msg=r_msg, group=group, extra={
                'template': 'Owner cannot quit from group: ${ID}',
                'replacements': {
                    'ID': str(group),
                }
            })
        assistants = facebook.assistants(identifier=group)
        if sender in assistants:
            return self._remove_assistant(content=content, sender=sender, msg=r_msg)
        # 2. remove sender from group members
        if sender in members:
            members.remove(sender)
            man = group_manager()
            man.save_members(members=members, group=group)
        # 3. response (no need to response this group command)
        return []


def group_manager():
    from ..group import GroupManager
    return GroupManager()
