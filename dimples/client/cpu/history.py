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
    Group History Processors
    ~~~~~~~~~~~~~~~~~~~~~~~~

"""

from typing import List

from dimsdk import ID, ReliableMessage
from dimsdk import Content
from dimsdk import Command, GroupCommand
from dimsdk import BaseCommandProcessor


class HistoryCommandProcessor(BaseCommandProcessor):

    # Override
    def process_content(self, content: Content, r_msg: ReliableMessage) -> List[Content]:
        assert isinstance(content, Command), 'history command error: %s' % content
        return self._respond_receipt(text='Command not support.', msg=r_msg, group=content.group, extra={
            'template': 'History command (name: ${command}) not support yet!',
            'replacements': {
                'command': content.cmd,
            }
        })


class GroupCommandProcessor(HistoryCommandProcessor):

    @staticmethod
    def members(content: GroupCommand) -> List[ID]:
        # get from 'members'
        array = content.members
        if array is None:
            # get from 'member
            item = content.member
            if item is None:
                array = []
            else:
                array = [item]
        return array

    # Override
    def process_content(self, content: Content, r_msg: ReliableMessage) -> List[Content]:
        assert isinstance(content, GroupCommand), 'group command error: %s' % content
        return self._respond_receipt(text='Command not support.', msg=r_msg, group=content.group, extra={
            'template': 'Group command (name: ${command}) not support yet!',
            'replacements': {
                'command': content.cmd,
            }
        })
