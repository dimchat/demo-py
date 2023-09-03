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
    2. owner and administrator cannot quit
"""

from typing import List

from dimsdk import ID
from dimsdk import ReliableMessage
from dimsdk import Content, ForwardContent
from dimsdk import QuitCommand

from .history import GroupCommandProcessor
from .history import create_reset_command, update_reset_command_message


class QuitCommandProcessor(GroupCommandProcessor):

    # Override
    def process_content(self, content: Content, r_msg: ReliableMessage) -> List[Content]:
        assert isinstance(content, QuitCommand), 'quit command error: %s' % content
        group = content.group
        # 0. check command
        if self._is_command_expired(command=content):
            # ignore expired command
            return []
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
        if sender == owner:
            return self._respond_receipt(text='Permission denied.', msg=r_msg, group=group, extra={
                'template': 'Owner cannot quit from group: ${ID}',
                'replacements': {
                    'ID': str(group),
                }
            })
        administrators = self.group_administrators(group=group)
        if sender in administrators:
            return self._respond_receipt(text='Permission denied.', msg=r_msg, group=group, extra={
                'template': 'Administrator cannot quit from group: ${ID}',
                'replacements': {
                    'ID': str(group),
                }
            })
        # 3. do quit
        members = members.copy()
        sender_is_member = sender in members
        if sender_is_member:
            # member do exist, remove it and update database
            members.remove(sender)
            if self.save_members(members=members, group=group):
                content['removed'] = [str(sender)]
        # 4. update 'reset' command
        user = self.facebook.current_user
        assert user is not None, 'failed to get current user'
        me = user.identifier
        if me == owner or me in administrators:
            # this is the group owner (or administrator), so
            # it has permission to reset group members here.
            self.__refresh_members(group=group, admin=me, members=members)
        else:
            # add 'quit' application for waiting admin to update
            self._add_application(command=content, message=r_msg)
        if not sender_is_member:
            return self._respond_receipt(text='Permission denied.', msg=r_msg, group=group, extra={
                'template': 'Not a member of group: ${ID}',
                'replacements': {
                    'ID': str(group),
                }
            })
        # no need to response this group command
        return []

    def __refresh_members(self, group: ID, admin: ID, members: List[ID]):
        messenger = self.messenger
        db = messenger.facebook.database
        # 1. create new 'reset' command
        cmd, msg = create_reset_command(sender=admin, group=group, members=members, messenger=messenger)
        if not update_reset_command_message(group=group, cmd=cmd, msg=msg, database=db):
            # failed to save 'reset' command message
            return False
        forward = ForwardContent.create(message=msg)
        # 2. forward to assistants
        assistants = self.group_assistants(group=group)
        for bot in assistants:
            assert bot != admin, 'group bot should not be admin: %s, %s, group: %s' % (admin, bot, group)
            messenger.send_content(sender=admin, receiver=bot, content=forward, priority=1)
        return True
