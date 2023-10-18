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

from dimsdk import ANYONE
from dimsdk import ID, Document
from dimsdk import InstantMessage, ReliableMessage
from dimsdk import Envelope, Content, DocumentCommand
from dimsdk import GroupCommand, ResetCommand, ResignCommand

from ..utils import Logging
from ..utils import is_before
from ..common import CommonFacebook, CommonMessenger

from .delegate import GroupDelegate
from .helper import GroupCommandHelper


class GroupHistoryBuilder(Logging):

    def __init__(self, delegate: GroupDelegate):
        super().__init__()
        self.__delegate = delegate
        self.__helper = self._create_helper()

    def _create_helper(self) -> GroupCommandHelper:
        """ override for customized helper """
        return GroupCommandHelper(self.delegate)

    @property  # protected
    def delegate(self) -> GroupDelegate:
        return self.__delegate

    @property  # protected
    def helper(self) -> GroupCommandHelper:
        return self.__helper

    @property  # protected
    def facebook(self) -> CommonFacebook:
        return self.delegate.facebook

    @property  # protected
    def messenger(self) -> CommonMessenger:
        return self.delegate.messenger

    def build_group_histories(self, group: ID) -> List[ReliableMessage]:
        """ build command list for group history:
                0. document command
                1. reset group command
                2. other group commands
        """
        messages = []
        #
        #  0. build 'document' command
        #
        pair = self.build_document_command(group=group)
        doc = pair[0]
        msg = pair[1]
        if doc is None or msg is None:
            self.warning(msg='failed to build "document" command for group: %s' % group)
            return messages
        else:
            messages.append(msg)
        #
        #  1. append 'reset' command
        #
        pair = self.helper.reset_command_message(group=group)
        reset = pair[0]
        msg = pair[1]
        if reset is None or msg is None:
            self.warning(msg='failed to get "reset" command for group: %s' % group)
            return messages
        else:
            messages.append(msg)
        #
        #  2. append other group commands
        #
        history = self.helper.group_histories(group=group)
        for pair in history:
            cmd = pair[0]
            msg = pair[1]
            if isinstance(cmd, ResetCommand):
                # 'reset' command already add to the front
                # assert len(messages) == 2, 'group history error: %d, %s' % (len(history), group)
                self.info(msg='skip "reset" command for group: %s' % group)
                continue
            elif isinstance(cmd, ResignCommand):
                # 'resign' command, comparing it with document time
                if is_before(old_time=doc.time, new_time=cmd.time):
                    self.warning(msg='expired "%s" command in group: %s, sender: %s' % (cmd.cmd, group, msg.sender))
                    continue
            else:
                # other commands('invite', 'join', 'quit'), comparing with 'reset' time
                if is_before(old_time=reset.time, new_time=cmd.time):
                    self.warning('expired "%s" command in group: %s, sender: %s' % (cmd.cmd, group, msg.sender))
                    continue
            messages.append(msg)
        # OK
        return messages

    def build_document_command(self, group: ID) -> Tuple[Optional[Document], Optional[ReliableMessage]]:
        """ create broadcast 'document' command """
        user = self.facebook.current_user
        doc = self.delegate.document(identifier=group)
        if user is None or doc is None:
            assert user is not None, 'failed to get current user'
            self.error(msg='document not found for group: %s' % group)
            return None, None
        me = user.identifier
        meta = self.delegate.meta(identifier=group)
        cmd = DocumentCommand.response(identifier=group, meta=meta, document=doc)
        msg = self.__pack_broadcast_message(sender=me, content=cmd)
        return doc, msg

    def builder_reset_command(self, group: ID,
                              members: Optional[List[ID]]) -> Tuple[Optional[ResetCommand], Optional[ReliableMessage]]:
        """ create broadcast 'reset' group command with newest member list """
        user = self.facebook.current_user
        owner = self.delegate.owner(identifier=group)
        if user is None or owner is None:
            assert user is not None, 'failed to get current user'
            self.error(msg='owner not found for group: %s' % group)
            return None, None
        me = user.identifier
        if owner != me:
            admins = self.delegate.administrators(group=group)
            if me not in admins:
                self.warning(msg='not permit to build "reset" command for group: %s, %s' % (group, me))
                return None, None
        if members is None:
            self.delegate.members(identifier=group)
        cmd = GroupCommand.reset(group=group, members=members)
        msg = self.__pack_broadcast_message(sender=me, content=cmd)
        return cmd, msg

    def __pack_broadcast_message(self, sender: ID, content: Content):
        envelope = Envelope.create(sender=sender, receiver=ANYONE)
        i_msg = InstantMessage.create(head=envelope, body=content)
        s_msg = self.messenger.encrypt_message(msg=i_msg)
        assert s_msg is not None, 'failed to encrypt message: %s' % envelope
        r_msg = self.messenger.sign_message(msg=s_msg)
        assert r_msg is not None, 'failed to sign message: %s' % envelope
        return r_msg
