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
    Command Processor for 'report'
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    Report protocol
"""

from typing import List

from dimsdk import ReliableMessage
from dimsdk import Content
from dimsdk import BaseCommandProcessor

from ...utils import Logging
from ...common import ReportCommand
from ...common import CommonMessenger, Session


class ReportCommandProcessor(BaseCommandProcessor, Logging):

    @property
    def session(self) -> Session:
        messenger = self.messenger
        assert isinstance(messenger, CommonMessenger), 'messenger error: %s' % messenger
        return messenger.session

    # Override
    def process_content(self, content: Content, r_msg: ReliableMessage) -> List[Content]:
        assert isinstance(content, ReportCommand), 'report command error: %s' % content
        # check session sender
        session = self.session
        sender = r_msg.sender
        if session.identifier is None:
            self.error(msg='session not login, drop report command: %s => %s' % (sender, content))
            return []
        assert sender == session.identifier, 'report sender error: %s not %s' % (sender, session.identifier)
        # check report title
        title = content.title
        if title == ReportCommand.ONLINE:
            # online
            session.set_active(active=True, when=content.time)
            return self._respond_receipt(text='Online received.', msg=r_msg, extra={
                'template': 'Online command received: ${ID}.',
                'replacements': {
                    'ID': str(sender),
                }
            })
        elif title == ReportCommand.OFFLINE:
            # offline
            session.set_active(active=False, when=content.time)
            # respond nothing when user offline
            return []
        else:
            return self._respond_receipt(text='Command not support.', msg=r_msg, extra={
                'template': 'Report command (title: ${title}) not support yet!',
                'replacements': {
                    'title': title,
                }
            })
