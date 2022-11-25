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
    Messenger for client
    ~~~~~~~~~~~~~~~~~~~~

    Transform and send message
"""

from typing import Optional

from dimsdk import EVERYONE
from dimsdk import DocumentCommand

from startrek.fsm import StateDelegate

from ..utils import Logging
from ..common import HandshakeCommand
from ..common import CommonFacebook, CommonMessenger
from ..common import MessageDBI

from .session import ClientSession
from .state import StateMachine, SessionState


class ClientMessenger(CommonMessenger, StateDelegate, Logging):

    def __init__(self, session: ClientSession, facebook: CommonFacebook, database: MessageDBI):
        super().__init__(session=session, facebook=facebook, database=database)
        # session state
        fsm = StateMachine(session=session)
        fsm.delegate = self
        self.__fsm = fsm

    @property
    def session(self) -> ClientSession:
        sess = super().session
        assert isinstance(sess, ClientSession), 'session error: %s' % sess
        return sess

    def start(self):
        self.session.start()
        self.__fsm.start()

    def stop(self):
        self.session.stop()
        self.__fsm.stop()

    def handshake(self, session_key: Optional[str]):
        """ send handshake command to current station """
        # 1. create handshake command
        if session_key is None:
            cmd = HandshakeCommand.start()
        else:
            cmd = HandshakeCommand.restart(session=session_key)
        # 2. send to remote station
        station = self.session.station
        self.send_content(sender=None, receiver=station.identifier, content=cmd, priority=-1)

    def broadcast_document(self):
        """ broadcast meta & visa document to all stations """
        facebook = self.facebook
        current = facebook.current_user
        identifier = current.identifier
        meta = current.meta
        visa = current.visa
        cmd = DocumentCommand.response(identifier=identifier, meta=meta, document=visa)
        self.send_content(sender=None, receiver=EVERYONE, content=cmd, priority=-1)

    #
    #   StateDelegate
    #

    # Override
    def enter_state(self, state: SessionState, ctx: StateMachine):
        # called before state changed
        session = self.session
        assert isinstance(session, ClientSession), 'session error: %s' % session
        station = session.station
        self.info(msg='enter state: %s, %s => %s' % (state, session.identifier, station.identifier))

    # Override
    def exit_state(self, state: SessionState, ctx: StateMachine):
        # called after state changed
        current = ctx.current_state
        self.info('server state changed: %s -> %s' % (state, current))
        if current is None:
            return
        elif current == SessionState.HANDSHAKING:
            # start handshake
            self.handshake(session_key=None)
        elif current == SessionState.RUNNING:
            # broadcast current meta & visa document to all stations
            self.broadcast_document()

    # Override
    def pause_state(self, state: SessionState, ctx: StateMachine):
        pass

    # Override
    def resume_state(self, state: SessionState, ctx: StateMachine):
        # TODO: clear session key for re-login?
        pass
