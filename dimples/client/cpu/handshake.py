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

from dimsdk import ReliableMessage
from dimsdk import Content

from dimsdk.cpu import BaseCommandProcessor

from ...utils import Logging
from ...common import HandshakeCommand


class HandshakeCommandProcessor(BaseCommandProcessor, Logging):

    # Override
    def process_content(self, content: Content, r_msg: ReliableMessage) -> List[Content]:
        assert isinstance(content, HandshakeCommand), 'handshake command error: %s' % content
        messenger = get_client_messenger(cpu=self)
        client_session = get_client_session(messenger=messenger)
        # update station's default ID ('station@anywhere') to sender (real ID)
        station = client_session.station
        oid = station.identifier
        sender = r_msg.sender
        if oid is None or oid.is_broadcast:
            station.identifier = sender
        else:
            # make sure handshake command from current station
            assert oid == sender, 'station ID not match: %s, %s' % (oid, sender)
        # handle handshake command with title & session key
        title = content.title
        new_sess_key = content.session
        old_sess_key = client_session.key
        assert new_sess_key is not None, 'new session key should not be empty: %s' % content
        if 'DIM?' == title:
            # S -> C: station ask client to handshake again
            self.info(msg='handshake again, session key: %s' % new_sess_key)
            # clear client session key while handshake again
            if old_sess_key is None:
                # first handshake response with new session key,
                messenger.handshake(session_key=new_sess_key)
            elif old_sess_key == new_sess_key:
                # duplicated handshake response?
                # or session expired and the station ask to handshake again?
                self.warning(msg='session key already set: %s => %s' % (old_sess_key, new_sess_key))
                messenger.handshake(session_key=new_sess_key)
            else:
                # connection changed?
                self.error(msg='session key from %s not match: %s => %s' % (sender, old_sess_key, new_sess_key))
                # erase session key to handshake again
                client_session.key = None
        elif 'DIM!' == title:
            # S -> C: handshake accepted by station
            self.info(msg='handshake success: %s, local: %s' % (station.identifier, client_session.identifier))
            # check session key
            if old_sess_key is None:
                # normal handshake response,
                # update session key to change state to 'running'
                client_session.key = new_sess_key
            elif old_sess_key == new_sess_key:
                # duplicated handshake response?
                pass
            else:
                # FIXME: handshake error
                self.error(msg='session key from %s not match: %s => %s' % (sender, old_sess_key, new_sess_key))
                # erase session key to handshake again
                client_session.key = None
        else:
            # C -> S: Hello world!
            self.error(msg='[Error] handshake command from %s: %s' % (sender, content))
        return []


#
#   getters
#


def get_client_messenger(cpu):
    messenger = cpu.messenger
    from ..messenger import ClientMessenger
    assert isinstance(messenger, ClientMessenger), 'messenger error: %s' % messenger
    return messenger


def get_client_session(messenger=None, cpu=None):
    if messenger is None:
        messenger = get_client_messenger(cpu=cpu)
    session = messenger.session
    from ..network.session import ClientSession
    assert isinstance(session, ClientSession), 'session error: %s' % session
    return session
