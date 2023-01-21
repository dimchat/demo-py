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
    Query Group Command Processor
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    1. query for group members-list
    2. any existed member or assistant can query group members-list
"""

from typing import List

from dimp import ID
from dimp import ReliableMessage
from dimp import Content
from dimp import QueryCommand

from .history import GroupCommandProcessor


class QueryCommandProcessor(GroupCommandProcessor):

    STR_QUERY_NOT_ALLOWED = 'Sorry, you are not allowed to query this group.'

    def _respond_group_members(self, owner: ID, group: ID, members: List[ID]) -> Content:
        # facebook = self.facebook
        # user = facebook.current_user
        # assert user is not None, 'current user not set'
        # if user.identifier == owner:
        #     return GroupCommand.reset(group=group, members=members)
        # else:
        #     return GroupCommand.invite(group=group, members=members)
        pass

    # Override
    def process(self, content: Content, msg: ReliableMessage) -> List[Content]:
        assert isinstance(content, QueryCommand), 'query command error: %s' % content
        facebook = self.facebook
        group = content.group
        owner = facebook.owner(identifier=group)
        members = facebook.members(identifier=group)
        # 0. check group
        if owner is None or members is None or len(members) == 0:
            text = self.STR_GROUP_EMPTY
            return self._respond_text(text=text, group=group)
        # 1. check permission
        sender = msg.sender
        if sender not in members:
            # not a member? check assistants
            assistants = facebook.assistants(identifier=group)
            if assistants is None or sender not in assistants:
                text = self.STR_QUERY_NOT_ALLOWED
                return self._respond_text(text=text, group=group)
        # 2. respond
        res = self._respond_group_members(owner=owner, group=group, members=members)
        return [] if res is None else [res]
