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

from typing import Optional, Tuple, List

from dimsdk import DateTime
from dimsdk import ID
from dimsdk import ReliableMessage
from dimsdk import GroupCommand, ResetCommand, ResignCommand
from dimsdk import DocumentUtils

from .delegate import TripletsHelper


class GroupCommandHelper(TripletsHelper):

    #
    #   Group History Command
    #

    async def save_group_history(self, group: ID, content: GroupCommand, message: ReliableMessage) -> bool:
        if await self.is_command_expired(content=content):
            self.warning(msg='drop expired command: %s, %s => %s' % (content.cmd, message.sender, group))
            return False
        # check command time
        cmd_time = content.time
        if cmd_time is None:
            self.error(msg='group command error: %s' % content)
        else:
            # calibrate the clock
            # make sure the command time is not in the far future
            near_future = DateTime.now() + 30 * 60
            if cmd_time > near_future:
                self.error(msg='group command time error: %s, %s' % (cmd_time, content))
                return False
        # update group history
        db = self.database
        if isinstance(content, ResetCommand):
            self.warning(msg='cleaning group history for "reset" command: %s => %s' % (message.sender, group))
            await db.clear_group_member_histories(group=group)
        return await db.save_group_history(group=group, content=content, message=message)

    async def get_group_histories(self, group: ID) -> List[Tuple[GroupCommand, ReliableMessage]]:
        db = self.database
        return await db.get_group_histories(group=group)

    async def get_reset_command_message(self, group: ID) -> Tuple[Optional[ResetCommand], Optional[ReliableMessage]]:
        db = self.database
        return await db.get_reset_command_message(group=group)

    async def clear_group_member_histories(self, group: ID) -> bool:
        db = self.database
        return await db.clear_group_member_histories(group=group)

    async def clear_group_admin_histories(self, group: ID) -> bool:
        db = self.database
        return await db.clear_group_admin_histories(group=group)

    async def is_command_expired(self, content: GroupCommand) -> bool:
        """ check command time
            (all group commands received must after the cached 'reset' command)
        """
        group = content.group
        assert group is not None, 'group content error: %s' % content
        if isinstance(content, ResignCommand):
            # administrator command, check with document time
            doc = await self.delegate.get_bulletin(group)
            if doc is None:
                self.error(msg='group document not exists: %s' % group)
                return True
            return DocumentUtils.is_before(old_time=doc.time, this_time=content.time)
        # membership command, check with reset command
        cmd, _ = await self.get_reset_command_message(group=group)
        if cmd is None:  # or msg is None:
            self.info(msg='"reset" command not found: %s' % content)
            return False
        return DocumentUtils.is_before(old_time=cmd.time, this_time=content.time)

    # noinspection PyMethodMayBeStatic
    def members_from_command(self, content: GroupCommand) -> List[ID]:
        # get from 'members'
        members = content.members
        if members is None:
            # get from 'member
            single = content.member
            members = [] if single is None else [single]
        return members
