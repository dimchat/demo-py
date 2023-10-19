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

from typing import Optional, List, Tuple

from dimsdk import ID
from dimsdk import ReliableMessage
from dimsdk import Content, ForwardContent
from dimsdk import Command, GroupCommand

from dimsdk.cpu import BaseCommandProcessor


from ...utils import Logging
from ...common import CommonFacebook, CommonMessenger
from ...group import GroupDelegate
from ...group import GroupCommandHelper
from ...group import GroupHistoryBuilder


class HistoryCommandProcessor(BaseCommandProcessor, Logging):

    def __init__(self, facebook: CommonFacebook, messenger: CommonMessenger):
        super().__init__(facebook=facebook, messenger=messenger)
        # lazy
        self.__delegate = None
        self.__helper = None
        self.__builder = None

    @property
    def facebook(self) -> CommonFacebook:
        barrack = super().facebook
        assert isinstance(barrack, CommonFacebook), 'barrack error: %s' % barrack
        return barrack

    @property
    def messenger(self) -> CommonMessenger:
        transceiver = super().messenger
        assert isinstance(transceiver, CommonMessenger), 'transceiver error: %s' % transceiver
        return transceiver

    # Override
    def process_content(self, content: Content, r_msg: ReliableMessage) -> List[Content]:
        assert isinstance(content, Command), 'history command error: %s' % content
        text = 'Command not support.'
        return self._respond_receipt(text=text, content=content, envelope=r_msg.envelope, extra={
            'template': 'History command (name: ${command}) not support yet!',
            'replacements': {
                'command': content.cmd,
            }
        })

    #
    #   Group History Delegates
    #

    @property  # protected
    def delegate(self) -> GroupDelegate:
        ds = self.__delegate
        if ds is None:
            self.__delegate = ds = self._create_delegate()
        return ds

    @property  # protected
    def helper(self) -> GroupCommandHelper:
        delegate = self.__helper
        if delegate is None:
            self.__helper = delegate = self._create_helper()
        return delegate

    @property  # protected
    def builder(self) -> GroupHistoryBuilder:
        delegate = self.__builder
        if delegate is None:
            self.__builder = delegate = self._create_builder()
        return delegate

    def _create_delegate(self) -> GroupDelegate:
        """ override for customized data source """
        return GroupDelegate(facebook=self.facebook, messenger=self.messenger)

    def _create_helper(self) -> GroupCommandHelper:
        """ override for customized helper """
        return GroupCommandHelper(delegate=self.delegate)

    def _create_builder(self) -> GroupHistoryBuilder:
        """ override for customized builder """
        return GroupHistoryBuilder(delegate=self.delegate)


class GroupCommandProcessor(HistoryCommandProcessor):

    def _owner(self, group: ID) -> Optional[ID]:
        delegate = self.delegate
        return delegate.owner(identifier=group)

    def _assistants(self, group: ID) -> List[ID]:
        delegate = self.delegate
        return delegate.assistants(identifier=group)

    def _administrators(self, group: ID) -> List[ID]:
        delegate = self.delegate
        return delegate.administrators(group=group)

    def _save_administrators(self, administrators: List[ID], group: ID) -> bool:
        delegate = self.delegate
        return delegate.save_administrators(administrators=administrators, group=group)

    def _members(self, group: ID) -> List[ID]:
        delegate = self.delegate
        return delegate.members(identifier=group)

    def _save_members(self, members: List[ID], group: ID) -> bool:
        delegate = self.delegate
        return delegate.save_members(members=members, group=group)

    def _save_group_history(self, group: ID, content: GroupCommand, r_msg: ReliableMessage) -> bool:
        delegate = self.helper
        return delegate.save_group_history(group=group, content=content, message=r_msg)

    # Override
    def process_content(self, content: Content, r_msg: ReliableMessage) -> List[Content]:
        assert isinstance(content, GroupCommand), 'group command error: %s' % content
        text = 'Command not support.'
        return self._respond_receipt(text=text, content=content, envelope=r_msg.envelope, extra={
            'template': 'Group command (name: ${command}) not support yet!',
            'replacements': {
                'command': content.cmd,
            }
        })

    def _check_expired(self, content: GroupCommand, r_msg: ReliableMessage) -> Tuple[Optional[ID], List[Content]]:
        group = content.group
        assert group is not None, 'group command error: %s' % content
        expired = self.helper.is_expired(content=content)
        if expired:
            text = 'Command expired.'
            errors = self._respond_receipt(text=text, content=content, envelope=r_msg.envelope, extra={
                'template': 'Group command expired: ${cmd}, group: ${ID}.',
                'replacements': {
                    'cmd': content.cmd,
                    'ID': str(group),
                }
            })
            group = None
        else:
            # group ID must not empty here
            errors = None
        return group, errors

    def _check_command_members(self, content: GroupCommand, r_msg: ReliableMessage) -> Tuple[List[ID], List[Content]]:
        group = content.group
        assert group is not None, 'group command error: %s' % content
        members = self.helper.members_from_command(content=content)
        if len(members) == 0:
            text = 'Command error.'
            errors = self._respond_receipt(text=text, content=content, envelope=r_msg.envelope, extra={
                'template': 'Group members empty: ${ID}.',
                'replacements': {
                    'ID': str(group),
                }
            })
        else:
            # normally
            errors = None
        return members, errors

    def _check_group_members(self, content: GroupCommand,
                             r_msg: ReliableMessage) -> Tuple[Optional[ID], List[ID], List[Content]]:
        group = content.group
        assert group is not None, 'group command error: %s' % content
        owner = self._owner(group=group)
        members = self._members(group=group)
        if owner is None or len(members) == 0:
            # TODO: query group members?
            text = 'Group empty.'
            errors = self._respond_receipt(text=text, content=content, envelope=r_msg.envelope, extra={
                'template': 'Group empty: ${ID}.',
                'replacements': {
                    'ID': str(group),
                }
            })
        else:
            # group is ready
            errors = None
        return owner, members, errors

    # protected
    def send_group_histories(self, group: ID, receiver: ID) -> bool:
        messages = self.builder.build_group_histories(group=group)
        if len(messages) == 0:
            self.warning(msg='failed to build history for group: %s' % group)
            return False
        content = ForwardContent.create(messages=messages)
        _, r_msg = self.messenger.send_content(sender=None, receiver=receiver, content=content, priority=1)
        return r_msg is not None
