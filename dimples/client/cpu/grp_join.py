# -*- coding: utf-8 -*-
#
#   DIM-SDK : Decentralized Instant Messaging Software Development Kit
#
#                                Written in 2023 by Moky <albert.moky@gmail.com>
#
# ==============================================================================
# MIT License
#
# Copyright (c) 2023 Albert Moky
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
    Join Group Command Processor
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    1. stranger can join a group
    2. only group owner or administrator can review this command
"""

from typing import List

from dimsdk import ReliableMessage
from dimsdk import Content
from dimsdk import JoinCommand

from .group import GroupCommandProcessor


class JoinCommandProcessor(GroupCommandProcessor):

    # Override
    def process_content(self, content: Content, r_msg: ReliableMessage) -> List[Content]:
        assert isinstance(content, JoinCommand), 'join command error: %s' % content

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
        admins = self._administrators(group=group)
        is_owner = sender == owner
        is_admin = sender in admins
        is_member = sender in members
        can_reset = is_owner or is_admin
        cannot_reset = not can_reset

        # 2. check membership
        if is_member:
            # maybe the command sender is already become a member,
            # but if it can still receive a 'join' command here,
            # we should notify the sender that the member list was updated.
            user = self.facebook.current_user
            if cannot_reset and owner == user.identifier:
                # the sender cannot reset the group, means it's an ordinary member now,
                # and if I am the owner, then send the group history commands
                # to update the sender's memory.
                ok = self.send_group_histories(group=group, receiver=sender)
                assert ok, 'failed to send history for group: %s => %s' % (group, sender)
        elif not self._save_group_history(group=group, content=content, r_msg=r_msg):
            # here try to append the 'join' command to local storage as group history
            # it should not failed unless the command is expired
            self.error(msg='failed to save "join" command for group: %s' % group)
        else:
            # the 'join' command was saved, now waiting for review.
            self.info(msg='"join" command saved, waiting review now')

        # no need to response this group command
        return []
