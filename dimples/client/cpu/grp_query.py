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

from dimsdk import ReliableMessage
from dimsdk import Content
from dimsdk import QueryCommand

from .group import GroupCommandProcessor


class QueryCommandProcessor(GroupCommandProcessor):

    # Override
    def process_content(self, content: Content, r_msg: ReliableMessage) -> List[Content]:
        assert isinstance(content, QueryCommand), 'query command error: %s' % content

        # 0. check command
        group, errors = self._check_expired(content=content, r_msg=r_msg)
        if group is None:
            # ignore expired command
            return errors

        # 1. check group
        owner, members, errors = self._check_group_members(content=content, r_msg=r_msg)
        if owner is None or len(members) == 0:
            return errors

        sender = r_msg.sender
        bots = self._assistants(group=group)
        is_member = sender in members
        is_bot = sender in bots
        can_query = is_member or is_bot

        # 2. check permission
        if not can_query:
            text = 'Permission denied.'
            return self._respond_receipt(text=text, content=content, envelope=r_msg.envelope, extra={
                'template': 'Not allowed to query members of group: ${ID}',
                'replacements': {
                    'ID': str(group),
                }
            })

        # 3. send newest group history commands
        ok = self.send_group_histories(group=group, receiver=sender)
        assert ok, 'failed to send history for group: %s => %s' % (group, sender)

        # no need to response this group command
        return []
