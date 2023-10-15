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

from typing import Optional, Union

from dimsdk import ContentType
from dimsdk import GroupCommand
from dimsdk import ContentProcessor

from dimsdk.cpu import BaseContentProcessor, BaseContentProcessorCreator

from ...common import HandshakeCommand, LoginCommand
from ...common import CommonFacebook, CommonMessenger

from .text import TextContentProcessor
from .handshake import HandshakeCommandProcessor
from .login import LoginCommandProcessor
from .group import HistoryCommandProcessor, GroupCommandProcessor
from .grp_invite import InviteCommandProcessor
from .grp_expel import ExpelCommandProcessor
from .grp_join import JoinCommandProcessor
from .grp_quit import QuitCommandProcessor
from .grp_reset import ResetCommandProcessor
from .grp_query import QueryCommandProcessor
from .grp_resign import ResignCommandProcessor


class ClientContentProcessorCreator(BaseContentProcessorCreator):

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
    def create_content_processor(self, msg_type: Union[int, ContentType]) -> Optional[ContentProcessor]:
        # text
        if msg_type == ContentType.TEXT.value:
            return TextContentProcessor(facebook=self.facebook, messenger=self.messenger)
        # history
        if msg_type == ContentType.HISTORY.value:
            return HistoryCommandProcessor(facebook=self.facebook, messenger=self.messenger)
        # default
        if msg_type == 0:
            return BaseContentProcessor(facebook=self.facebook, messenger=self.messenger)
        # others
        return super().create_content_processor(msg_type=msg_type)

    # Override
    def create_command_processor(self, msg_type: Union[int, ContentType], cmd: str) -> Optional[ContentProcessor]:
        # handshake
        if cmd == HandshakeCommand.HANDSHAKE:
            return HandshakeCommandProcessor(facebook=self.facebook, messenger=self.messenger)
        # login
        if cmd == LoginCommand.LOGIN:
            return LoginCommandProcessor(facebook=self.facebook, messenger=self.messenger)
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
