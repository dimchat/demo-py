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

import time
from typing import List, Optional, Union

from dimsdk import EntityType
from dimsdk import ReliableMessage
from dimsdk import Content, ContentType, Command
from dimsdk import TextContent, ReceiptCommand
from dimsdk import ContentProcessor, ContentProcessorCreator
from dimsdk import MessageProcessor
from dimsdk import BaseContentProcessor, BaseContentProcessorCreator

from ..utils import Logging
from ..common import HandshakeCommand, LoginCommand
from ..common import ReportCommand, AnsCommand
from ..common import CommonMessenger

from .cpu import HandshakeCommandProcessor
from .cpu import LoginCommandProcessor
from .cpu import ReportCommandProcessor
from .cpu import AnsCommandProcessor

from .cpu import DocumentCommandProcessor


class ServerMessageProcessor(MessageProcessor, Logging):

    @property
    def messenger(self) -> CommonMessenger:
        transceiver = super().messenger
        assert isinstance(transceiver, CommonMessenger), 'messenger error: %s' % transceiver
        return transceiver

    # Override
    def process_content(self, content: Content, r_msg: ReliableMessage) -> List[Content]:
        # 0. process first
        responses = super().process_content(content=content, r_msg=r_msg)
        messenger = self.messenger
        sender = r_msg.sender
        # 1. check login
        session = messenger.session
        if session.identifier is None:  # or not session.active:
            # not login yet, force to handshake again
            if not isinstance(content, HandshakeCommand):
                handshake = HandshakeCommand.ask(session=session.key)
                responses.insert(0, handshake)
        # 2. check response
        contents = []
        for res in responses:
            if res is None:
                # should not happen
                continue
            elif isinstance(res, ReceiptCommand):
                if sender.type == EntityType.STATION:
                    # no need to respond receipt to station
                    when = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(r_msg.time))
                    self.info(msg='drop receipt responding to %s, origin msg time=[%s]' % (sender, when))
                    continue
            elif isinstance(res, TextContent):
                if sender.type == EntityType.STATION:
                    # no need to respond text message to station
                    when = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(r_msg.time))
                    self.info(msg='drop text responding to %s, origin time=[%s], text=%s' % (sender, when, res.text))
                    continue
            contents.append(res)
        # OK
        return contents

    # Override
    def _create_creator(self) -> ContentProcessorCreator:
        return ServerContentProcessorCreator(facebook=self.facebook, messenger=self.messenger)


class ServerContentProcessorCreator(BaseContentProcessorCreator):

    # Override
    def create_content_processor(self, msg_type: Union[int, ContentType]) -> Optional[ContentProcessor]:
        # default
        if msg_type == 0:
            return BaseContentProcessor(facebook=self.facebook, messenger=self.messenger)
        # others
        return super().create_content_processor(msg_type=msg_type)

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
