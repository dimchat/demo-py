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

from typing import Optional, List

from dimsdk import DateTime
from dimsdk import ID, Content, ReliableMessage

from dimsdk.cpu import BaseCommandProcessor

from ...utils import Log
from ...common import HandshakeCommand
from ...common import CommonMessenger, Session


class HandshakeCommandProcessor(BaseCommandProcessor):

    @property
    def messenger(self) -> CommonMessenger:
        transceiver = super().messenger
        assert isinstance(transceiver, CommonMessenger), 'messenger error: %s' % transceiver
        return transceiver

    # Override
    def process_content(self, content: Content, r_msg: ReliableMessage) -> List[Content]:
        assert isinstance(content, HandshakeCommand), 'handshake command error: %s' % content
        title = content.title
        if title in ['DIM?', 'DIM!']:
            # S -> C
            text = 'Command not support.'
            return self._respond_receipt(text=text, envelope=r_msg.envelope, content=content, extra={
                'template': 'Handshake command error: title="${title}".',
                'replacements': {
                    'title': title,
                }
            })
        # C -> S: Hello world!
        assert 'Hello world!' == title, 'Handshake command error: %s' % content
        # set/update session in session server with new session key
        messenger = self.messenger
        session = messenger.session
        sess_id = session.identifier
        sender = r_msg.sender
        if sess_id is not None:
            assert sess_id == sender, 'sender error: %s, %s' % (sender, sess_id)
        if session.key == content.session:
            # session key match
            Log.info(msg='handshake accepted: %s, session: %s' % (sender, session.key))
            # verified success
            handshake_accepted(identifier=sender, when=content.time, session=session, messenger=messenger)
            res = HandshakeCommand.success(session=session.key)
        else:
            # session key not match
            # ask client to sign it with the new session key
            res = HandshakeCommand.again(session=session.key)
        res['remote_address'] = session.remote_address
        return [res]


def handshake_accepted(identifier: ID, when: Optional[DateTime], session: Session, messenger: CommonMessenger):
    from ..session_center import SessionCenter
    center = SessionCenter()
    # 1. update session ID
    center.update_session(session=session, identifier=identifier)
    # 2. update session flag
    session.set_active(active=True, when=when)
    # 3. callback
    messenger.handshake_success()
