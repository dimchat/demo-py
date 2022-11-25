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

from dimsdk import Station
from dimsdk import ReliableMessage
from dimsdk import Content
from dimsdk import BaseCommandProcessor

from ...utils import Logging
from ...common import HandshakeCommand


class HandshakeCommandProcessor(BaseCommandProcessor, Logging):

    # Override
    def process(self, content: Content, msg: ReliableMessage) -> List[Content]:
        assert isinstance(content, HandshakeCommand), 'handshake command error: %s' % content
        messenger = get_client_messenger(cpu=self)
        client_session = get_client_session(messenger=messenger)
        sender = msg.sender
        title = content.title
        new_sess_key = content.session
        if 'DIM?' == title:
            # S -> C: station ask client to handshake again
            self.info(msg='handshake again, session key: %s' % new_sess_key)
            # 1. replace station id (default is 'station@anywhere')
            station = client_session.station
            oid = station.identifier
            if oid is None or oid == Station.ANY:
                station.identifier = sender
            else:
                assert oid == sender, 'station ID not match: %s, %s' % (oid, sender)
            assert client_session.key is None, 'session key should be empty while handshaking'
            # 2. send handshake command with new session key
            messenger.handshake(session_key=new_sess_key)
        elif 'DIM!' == title:
            # S -> C: handshake accepted by station
            self.info(msg='handshake success!')
            assert client_session.key is None, 'session key should be empty while handshaking'
            # update session key to change session state to 'running'
            client_session.key = new_sess_key
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
    from ..session import ClientSession
    assert isinstance(session, ClientSession), 'session error: %s' % session
    return session
