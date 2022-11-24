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

from dimsdk import EntityType, ID
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
        sender = msg.sender
        title = content.title
        session_key = content.session
        if 'DIM?' == title:
            # S -> C: station ask client to handshake again
            self.info(msg='handshake again, session key: %s' % session_key)
            handshake_again(session_key=session_key, sid=sender, cpu=self)
        elif 'DIM!' == title:
            # S -> C: handshake accepted by station
            self.info(msg='handshake success!')
            # TODO: post current document to station
            handshake_success(session_key=session_key, cpu=self)
        else:
            # C -> S: Hello world!
            self.error(msg='[Error] handshake command from %s: %s' % (sender, content))
        return []


def handshake_again(session_key: str, sid: ID, cpu):
    assert sid.type == EntityType.STATION, 'station ID error: %s' % sid
    messenger = get_messenger(cpu=cpu)
    session = get_session(messenger=messenger)
    assert session.key is None, 'session key should be empty while handshaking'
    # 1. check station ID
    station = session.station
    oid = station.identifier
    if oid is None or oid == Station.ANY:
        station.identifier = sid
    else:
        assert oid == sid, 'station ID not match: %s, %s' % (oid, sid)
    # 2. handshake again
    uid = session.identifier
    # assert uid is not None, 'session ID should not be empty'
    cmd = HandshakeCommand.restart(session=session_key)
    messenger.send_content(sender=uid, receiver=sid, content=cmd, priority=-1)


def handshake_success(session_key: str, cpu):
    messenger = get_messenger(cpu=cpu)
    session = get_session(messenger=messenger)
    assert session.key is None, 'session key should be empty while handshaking'
    # 1. update session key to change session state to 'ready'
    session.key = session_key
    # 2. broadcast login command
    messenger.broadcast_login_command()


#
#   getters
#


def get_messenger(cpu):
    messenger = cpu.messenger
    from ..messenger import ClientMessenger
    assert isinstance(messenger, ClientMessenger), 'messenger error: %s' % messenger
    return messenger


def get_session(messenger=None, cpu=None):
    if messenger is None:
        messenger = get_messenger(cpu=cpu)
    session = messenger.session
    from ..session import ClientSession
    assert isinstance(session, ClientSession), 'session error: %s' % session
    return session
