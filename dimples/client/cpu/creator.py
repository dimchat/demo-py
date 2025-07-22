# -*- coding: utf-8 -*-
# ==============================================================================
# MIT License
#
# Copyright (c) 2021 Albert Moky
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
    Client extensions for MessageProcessor
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
"""

from typing import Optional

from dimsdk import ContentType
from dimsdk import Command, GroupCommand
from dimsdk import ContentProcessor
from dimsdk import Facebook, Messenger

from dimsdk.cpu import BaseContentProcessorCreator

from ...common import HandshakeCommand, LoginCommand, AnsCommand
from ...common import GroupHistory

from .handshake import HandshakeCommandProcessor
from .commands import AnsCommandProcessor, LoginCommandProcessor, ReceiptCommandProcessor
from .group import HistoryCommandProcessor, GroupCommandProcessor
from .grp_invite import InviteCommandProcessor
from .grp_expel import ExpelCommandProcessor
from .grp_join import JoinCommandProcessor
from .grp_quit import QuitCommandProcessor
from .grp_reset import ResetCommandProcessor
from .grp_query import QueryCommandProcessor
from .grp_resign import ResignCommandProcessor

from .customized import GroupHistoryHandler
from .customized import AppCustomizedProcessor


class ClientContentProcessorCreator(BaseContentProcessorCreator):

    # noinspection PyMethodMayBeStatic
    def _create_customized_content_processor(self, facebook: Facebook, messenger: Messenger) -> AppCustomizedProcessor:
        cpu = AppCustomizedProcessor(facebook=facebook, messenger=messenger)
        # 'chat.dim.group:history'
        handler = GroupHistoryHandler(facebook=facebook, messenger=messenger)
        cpu.set_handler(app=GroupHistory.APP, mod=GroupHistory.MOD, handler=handler)
        return cpu

    # Override
    def create_content_processor(self, msg_type: str) -> Optional[ContentProcessor]:
        # application customized
        if msg_type == ContentType.APPLICATION or msg_type == 'application':
            return self._create_customized_content_processor(facebook=self.facebook, messenger=self.messenger)
        elif msg_type == ContentType.CUSTOMIZED or msg_type == 'customized':
            return self._create_customized_content_processor(facebook=self.facebook, messenger=self.messenger)
        # history command
        if msg_type == ContentType.HISTORY or msg_type == 'history':
            return HistoryCommandProcessor(facebook=self.facebook, messenger=self.messenger)
        # others
        return super().create_content_processor(msg_type=msg_type)

    # Override
    def create_command_processor(self, msg_type: str, cmd: str) -> Optional[ContentProcessor]:
        # receipt
        if cmd == Command.RECEIPT:
            return ReceiptCommandProcessor(facebook=self.facebook, messenger=self.messenger)
        # handshake
        if cmd == HandshakeCommand.HANDSHAKE:
            return HandshakeCommandProcessor(facebook=self.facebook, messenger=self.messenger)
        # login
        if cmd == LoginCommand.LOGIN:
            return LoginCommandProcessor(facebook=self.facebook, messenger=self.messenger)
        # ans
        if cmd == AnsCommand.ANS:
            return AnsCommandProcessor(facebook=self.facebook, messenger=self.messenger)
        # group commands
        if cmd == 'group':
            return GroupCommandProcessor(facebook=self.facebook, messenger=self.messenger)
        elif cmd == GroupCommand.INVITE:
            return InviteCommandProcessor(facebook=self.facebook, messenger=self.messenger)
        elif cmd == GroupCommand.EXPEL:
            # Deprecated (use 'reset' instead)
            return ExpelCommandProcessor(facebook=self.facebook, messenger=self.messenger)
        elif cmd == GroupCommand.JOIN:
            return JoinCommandProcessor(facebook=self.facebook, messenger=self.messenger)
        elif cmd == GroupCommand.QUIT:
            return QuitCommandProcessor(facebook=self.facebook, messenger=self.messenger)
        elif cmd == GroupCommand.QUERY:
            return QueryCommandProcessor(facebook=self.facebook, messenger=self.messenger)
        elif cmd == GroupCommand.RESET:
            return ResetCommandProcessor(facebook=self.facebook, messenger=self.messenger)
        elif cmd == GroupCommand.RESIGN:
            return ResignCommandProcessor(facebook=self.facebook, messenger=self.messenger)
        # others
        return super().create_command_processor(msg_type=msg_type, cmd=cmd)
