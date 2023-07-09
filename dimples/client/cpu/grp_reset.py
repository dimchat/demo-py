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

from typing import List

from dimp import ID
from dimp import ReliableMessage
from dimp import Content
from dimp import GroupCommand, InviteCommand, ResetCommand

from ...common import CommonMessenger

from .history import GroupCommandProcessor


class ResetCommandProcessor(GroupCommandProcessor):

    def _query_owner(self, owner: ID, group: ID):
        command = GroupCommand.query(group=group)
        messenger = self.messenger
        assert isinstance(messenger, CommonMessenger), 'messenger error: %s' % messenger
        messenger.send_content(sender=None, receiver=owner, content=command, priority=1)

    def _temporary_save(self, content: GroupCommand, sender: ID, msg: ReliableMessage) -> List[Content]:
        facebook = self.facebook
        group = content.group
        # check whether the owner contained in the new members
        new_members = self.members(content=content)
        if new_members is None or len(new_members) == 0:
            return self._respond_receipt(text='Command error.', msg=msg, group=group, extra={
                'template': 'New member list is empty: ${ID}',
                'replacements': {
                    'ID': str(group),
                }
            })
        man = group_manager()
        for item in new_members:
            if facebook.meta(identifier=item) is None:
                # TODO: waiting for member's meta?
                continue
            elif not man.is_owner(member=item, group=group):
                # not owner, skip it
                continue
            # it's a full list, save it now
            if man.save_members(members=new_members, group=group):
                if item != sender:
                    # NOTICE: to prevent counterfeit,
                    #         query the owner for newest member-list
                    self._query_owner(owner=item, group=group)
            # response (no need to respond this group command)
            return []
        # NOTICE: this is a partial member-list
        #         query the sender for full-list
        query = GroupCommand.query(group=group)
        return [query]

    # Override
    def process(self, content: Content, msg: ReliableMessage) -> List[Content]:
        assert isinstance(content, InviteCommand) or isinstance(content, ResetCommand), 'group cmd error: %s' % content
        facebook = self.facebook
        # from ..facebook import Facebook
        # assert isinstance(facebook, Facebook)
        group = content.group
        owner = facebook.owner(identifier=group)
        members = facebook.members(identifier=group)
        # 0. check group
        if owner is None or members is None or len(members) == 0:
            # FIXME: group profile lost?
            # FIXME: how to avoid strangers impersonating group members?
            return self._temporary_save(content=content, sender=msg.sender, msg=msg)
        # 1. check permission
        sender = msg.sender
        if sender != owner:
            # not the owner? check assistants
            assistants = facebook.assistants(identifier=group)
            if assistants is None or sender not in assistants:
                return self._respond_receipt(text='Permission denied.', msg=msg, group=group, extra={
                    'template': 'Not allowed to reset members of group: ${ID}',
                    'replacements': {
                        'ID': str(group),
                    }
                })
        # 2. resetting members
        new_members = self.members(content=content)
        if new_members is None or len(new_members) == 0:
            return self._respond_receipt(text='Command error.', msg=msg, group=group, extra={
                'template': 'New member list is empty: ${ID}',
                'replacements': {
                    'ID': str(group),
                }
            })
        # 2.1. check owner
        if owner not in new_members:
            return self._respond_receipt(text='Permission denied.', msg=msg, group=group, extra={
                'template': 'Owner not in the new member list of group: ${ID}',
                'replacements': {
                    'ID': str(group),
                }
            })
        # 2.2. build expelled-list
        remove_list = []
        for item in members:
            if item not in new_members:
                # removing member found
                remove_list.append(item)
        # 2.3. build invited-list
        add_list = []
        for item in new_members:
            if item not in members:
                # adding member found
                add_list.append(item)
        # 2.4. do reset
        if len(add_list) > 0 or len(remove_list) > 0:
            man = group_manager()
            if man.save_members(members=new_members, group=group):
                if len(add_list) > 0:
                    content['added'] = ID.revert(add_list)
                if len(remove_list) > 0:
                    content['removed'] = ID.revert(remove_list)
        # 3. response (no need to response this group command)
        return []


def group_manager():
    from ..group import GroupManager
    return GroupManager()
