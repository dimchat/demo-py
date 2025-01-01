# -*- coding: utf-8 -*-
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
    Command Processor for 'login'
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    login protocol
"""

from typing import Optional, List

from dimsdk import ReliableMessage
from dimsdk import Content
from dimsdk import ReceiptCommand

from dimsdk.cpu import BaseCommandProcessor

from ...utils import Logging
from ...common import SessionDBI
from ...common import AnsCommand
from ...common import LoginCommand
from ...common import CommonMessenger

from ...group import SharedGroupManager

from ..facebook import ClientFacebook


class AnsCommandProcessor(BaseCommandProcessor, Logging):

    # Override
    async def process_content(self, content: Content, r_msg: ReliableMessage) -> List[Content]:
        assert isinstance(content, AnsCommand), 'ans command error: %s' % content
        records = content.records
        if records is None:
            self.info(msg='ANS: querying %s' % content.names)
        else:
            ans = ClientFacebook.ans
            if ans is None:
                count = -1
            else:
                count = ans.fix(records=records)
            self.info(msg='ANS: update %d record(s): %s' % (count, records))
        return []


class LoginCommandProcessor(BaseCommandProcessor, Logging):

    @property
    def database(self) -> Optional[SessionDBI]:
        messenger = self.messenger
        if isinstance(messenger, CommonMessenger):
            return messenger.session.database

    # Override
    async def process_content(self, content: Content, r_msg: ReliableMessage) -> List[Content]:
        assert isinstance(content, LoginCommand), 'login command error: %s' % content
        sender = content.identifier
        assert sender == r_msg.sender, 'sender not match: %s, %s' % (sender, r_msg.sender)
        # save login command to session db
        db = self.database
        if await db.save_login_command_message(user=sender, content=content, msg=r_msg):
            self.info(msg='save login command for user: %s' % sender)
        else:
            self.error(msg='failed to save login command: %s, %s' % (sender, content))
        return []


class ReceiptCommandProcessor(BaseCommandProcessor):

    # Override
    async def process_content(self, content: Content, r_msg: ReliableMessage) -> List[Content]:
        assert isinstance(content, ReceiptCommand), 'receipt command error: %s' % content
        man = SharedGroupManager()
        man.delegate.update_respond_time(content=content, envelope=r_msg.envelope)
        return []
