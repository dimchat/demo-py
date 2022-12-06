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
    Command Processor for 'handshake'
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    Handshake Protocol
"""

from typing import List

from dimsdk import ID
from dimsdk import ReliableMessage
from dimsdk import Content
from dimsdk import BaseCommandProcessor

from ...common import HandshakeCommand
from ...common import CommonMessenger, Session


class HandshakeCommandProcessor(BaseCommandProcessor):

    @property
    def session(self) -> Session:
        messenger = self.messenger
        assert isinstance(messenger, CommonMessenger), 'messenger error: %s' % messenger
        return messenger.session

    # Override
    def process(self, content: Content, msg: ReliableMessage) -> List[Content]:
        assert isinstance(content, HandshakeCommand), 'handshake command error: %s' % content
        title = content.title
        if title in ['DIM?', 'DIM!']:
            # S -> C
            text = 'Handshake command error: %s' % title
            return self._respond_text(text=text)
        # C -> S: Hello world!
        assert 'Hello world!' == title, 'Handshake command error: %s' % content
        # set/update session in session server with new session key
        session = self.session
        if session.key == content.session:
            # session key match
            # verified success
            handshake_accepted(identifier=msg.sender, session=session)
            res = HandshakeCommand.success(session=session.key)
        else:
            # session key not match
            # ask client to sign it with the new session key
            res = HandshakeCommand.again(session=session.key)
        return [res]


def handshake_accepted(identifier: ID, session: Session):
    # 1. update session ID
    from ..session_center import SessionCenter
    center = SessionCenter()
    center.update_session(session=session, identifier=identifier)
    # 2. update session flag
    session.set_active(active=True)
