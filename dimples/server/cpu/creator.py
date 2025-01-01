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
    Server extensions for MessageProcessor
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
"""

from typing import Optional, Union

from dimsdk import ContentType, Command
from dimsdk import ContentProcessor

from dimsdk.cpu import BaseContentProcessorCreator

from ...common import HandshakeCommand, LoginCommand
from ...common import ReportCommand, AnsCommand

from .handshake import HandshakeCommandProcessor
from .login import LoginCommandProcessor
from .report import ReportCommandProcessor
from .ans import AnsCommandProcessor

from .document import DocumentCommandProcessor


class ServerContentProcessorCreator(BaseContentProcessorCreator):

    # Override
    def create_command_processor(self, msg_type: Union[int, ContentType], cmd: str) -> Optional[ContentProcessor]:
        # document
        if cmd == Command.DOCUMENT:
            return DocumentCommandProcessor(facebook=self.facebook, messenger=self.messenger)
        # handshake
        if cmd == HandshakeCommand.HANDSHAKE:
            return HandshakeCommandProcessor(facebook=self.facebook, messenger=self.messenger)
        # login
        if cmd == LoginCommand.LOGIN:
            return LoginCommandProcessor(facebook=self.facebook, messenger=self.messenger)
        # report
        if cmd == ReportCommand.REPORT:
            return ReportCommandProcessor(facebook=self.facebook, messenger=self.messenger)
        # ans
        if cmd == AnsCommand.ANS:
            return AnsCommandProcessor(facebook=self.facebook, messenger=self.messenger)
        # others
        return super().create_command_processor(msg_type=msg_type, cmd=cmd)
