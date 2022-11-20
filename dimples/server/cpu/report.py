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
    def process(self, content: Content, msg: ReliableMessage) -> List[Content]:
        assert isinstance(content, ReportCommand), 'report command error: %s' % content
        # report title
        session = self.session
        db = session.database
        sender = msg.sender
        assert sender == session.identifier, 'report sender error: %s not %s' % (sender, session.identifier)
        title = content.title
        if title == ReportCommand.ONLINE:
            # online
            if db.save_online_command(identifier=sender, cmd=content):
                session.active = True
            text = 'Online command received.'
            return self._respond_text(text=text)
        elif title == ReportCommand.OFFLINE:
            # offline
            if db.save_online_command(identifier=sender, cmd=content):
                session.active = False
            text = 'Offline command received.'
            return self._respond_text(text=text)
        else:
            text = 'Report command (title: %s) not support yet!' % title
            return self._respond_text(text=text)
