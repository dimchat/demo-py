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

    3. specially, if the group members info lost,
       means you may not known who's the group owner immediately (and he may be not online),
       so we accept the new members-list temporary, and find out who is the owner,
       after that, we will send 'query' to the owner to get the newest members-list.
"""

from typing import Optional, Tuple, List

from dimsdk import ID
from dimsdk import ReliableMessage
from dimsdk import Content
from dimsdk import ResetCommand

from .history import GroupCommandProcessor


class ResetCommandProcessor(GroupCommandProcessor):

    # Override
    def process_content(self, content: Content, r_msg: ReliableMessage) -> List[Content]:
        assert isinstance(content, ResetCommand), 'group cmd error: %s' % content
        group = content.group
        # 0. check command
        new_members = self.command_members(content=content)
        if len(new_members) == 0:
            return self._respond_receipt(text='Command error.', msg=r_msg, group=group, extra={
                'template': 'New member list is empty: ${ID}',
                'replacements': {
                    'ID': str(group),
                }
            })
        # 1. check group
        owner = self.group_owner(group=group)
        members = self.group_members(group=group)
        if owner is None or len(members) == 0:
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
                'template': 'Not allowed to reset members of group: ${ID}',
                'replacements': {
                    'ID': str(group),
                }
            })
        # 2.1. check owner
        if owner != new_members[0]:
            return self._respond_receipt(text='Permission denied.', msg=r_msg, group=group, extra={
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
            return self._respond_receipt(text='Permission denied.', msg=r_msg, group=group, extra={
                'template': 'Not allowed to expel administrator of group: ${ID}',
                'replacements': {
                    'ID': str(group),
                }
            })
        # 3. do reset
        add_list, remove_list = self.__reset_members(group=group, old_members=members, new_members=new_members)
        if add_list is not None and len(add_list) > 0:
            content['added'] = ID.revert(add_list)
        if remove_list is not None and len(remove_list) > 0:
            content['removed'] = ID.revert(remove_list)
        # 4. save the reset command
        user = self.facebook.current_user
        if user.identifier == owner or user.identifier in administrators:
            # this is the group owner (or administrator),
            # it has permission to reset group members, so
            # no need to save the reset command here.
            pass
        else:
            # this is a group bot, it has no permission to change group members,
            # so save the reset command here for next querying from other members.
            db = self.facebook.database
            db.save_reset_command_message(group=group, content=content, msg=r_msg)
        # no need to response this group command
        return []

    def __reset_members(self, group: ID, old_members: List[ID],
                        new_members: List[ID]) -> Tuple[Optional[List[ID]], Optional[List[ID]]]:
        # build invited-list
        add_list = []
        for item in new_members:
            if item not in old_members:
                # adding member found
                add_list.append(item)
        # build expelled-list
        remove_list = []
        for item in old_members:
            if item not in new_members:
                # removing member found
                remove_list.append(item)
        if len(add_list) == 0 and len(remove_list) == 0:
            # nothing changed
            return None, None
        if self.save_members(members=new_members, group=group):
            return add_list, remove_list
        assert False, 'failed to save members in group: %s, %s' % (group, new_members)
