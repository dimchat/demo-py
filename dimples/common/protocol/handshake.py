# -*- coding: utf-8 -*-
#
#   DIMP : Decentralized Instant Messaging Protocol
#
#                                Written in 2019 by Moky <albert.moky@gmail.com>
#
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
    Handshake Command Protocol
    ~~~~~~~~~~~~~~~~~~~~~~~~~~

    1. (C-S) handshake start
    2. (S-C) handshake again with new session
    3. (C-S) handshake start with new session
    4. (S-C) handshake success
"""

from enum import IntEnum
from typing import Optional, Any, Dict

from dimsdk import Command, BaseCommand


class HandshakeState(IntEnum):
    Start = 0    # C -> S, without session key(or session expired)
    Again = 1    # S -> C, with new session key
    Restart = 2  # C -> S, with new session key
    Success = 3  # S -> C, handshake accepted


class HandshakeCommand(BaseCommand):
    """
        Handshake Command
        ~~~~~~~~~~~~~~~~~

        data format: {
            type : 0x88,
            sn   : 123,

            cmd     : "handshake",    // command name
            title   : "Hello world!", // "DIM?", "DIM!"
            session : "{SESSION_ID}", // session key
        }
    """
    HANDSHAKE = 'handshake'

    def __init__(self, content: Dict[str, Any] = None, title: str = None, session: str = None):
        if content is None:
            # create with title, session key
            super().__init__(cmd=self.HANDSHAKE)
            assert title is not None, 'new handshake command error'
            self['title'] = title
            if session is not None:
                self['session'] = session
        else:
            # create with command content
            super().__init__(content=content)
            if title is None:
                title = content.get('title')
            if session is None:
                session = content.get('session')
        # check state
        self.__state = handshake_state(title=title, session=session)

    @property
    def title(self) -> str:
        return self.get('title')

    @property
    def session(self) -> Optional[str]:
        return self.get('session')

    @property
    def state(self) -> HandshakeState:
        return self.__state

    #
    #   Factories
    #

    @classmethod
    def offer(cls, session: str = None) -> Command:
        """
        Create client-station handshake offer

        :param session: Old session key
        :return: HandshakeCommand object
        """
        return HandshakeCommand(title='Hello world!', session=session)

    @classmethod
    def ask(cls, session: str) -> Command:
        """
        Create station-client handshake again with new session

        :param session: New session key
        :return: HandshakeCommand object
        """
        return HandshakeCommand(title='DIM?', session=session)

    @classmethod
    def accepted(cls, session: str = None) -> Command:
        """
        Create station-client handshake success notice

        :return: HandshakeCommand object
        """
        return HandshakeCommand(title='DIM!', session=session)

    start = offer       # (1. C->S) first handshake, without session
    again = ask         # (2. S->C) ask client to handshake with new session key
    restart = offer     # (3. C->S) handshake with new session key
    success = accepted  # (4. S->C) notice the client that handshake accepted


def handshake_state(title: str, session: str = None) -> HandshakeState:
    # Server -> Client
    if title == 'DIM!':  # or title == 'OK!':
        return HandshakeState.Success
    if title == 'DIM?':
        return HandshakeState.Again
    # Client -> Server: "Hello world!"
    if session is None or len(session) == 0:
        return HandshakeState.Start
    else:
        return HandshakeState.Restart
