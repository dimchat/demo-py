# -*- coding: utf-8 -*-
# ==============================================================================
# MIT License
#
# Copyright (c) 2022 Albert Moky
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
    Terminal
    ~~~~~~~~

    Client
"""

import threading

from startrek.fsm import StateDelegate

from ..utils import Runner, Logging

from .session import ClientSession
from .state import StateMachine, SessionState
from .messenger import ClientMessenger


class Terminal(Runner, StateDelegate, Logging):

    def __init__(self, messenger: ClientMessenger):
        super().__init__()
        self.__messenger = messenger
        # session state
        fsm = StateMachine(session=messenger.session)
        fsm.delegate = self
        self.__fsm = fsm

    @property
    def messenger(self) -> ClientMessenger:
        return self.__messenger

    @property
    def session(self) -> ClientSession:
        sess = self.messenger.session
        assert isinstance(sess, ClientSession), 'session error: %s' % sess
        return sess

    def start(self):
        thread = threading.Thread(target=self.run, daemon=True)
        thread.start()

    # Override
    def setup(self):
        super().setup()
        self.session.start()
        self.__fsm.start()

    # Override
    def finish(self):
        self.__fsm.stop()
        self.session.stop()
        super().finish()

    # Override
    def process(self) -> bool:
        pass

    #
    #   StateDelegate
    #

    # Override
    def enter_state(self, state: SessionState, ctx: StateMachine):
        # called before state changed
        session = self.session
        station = session.station
        self.info(msg='enter state: %s, %s => %s' % (state, session.identifier, station.identifier))

    # Override
    def exit_state(self, state: SessionState, ctx: StateMachine):
        # called after state changed
        current = ctx.current_state
        self.info(msg='server state changed: %s -> %s' % (state, current))
        if current is None:
            return
        elif current == SessionState.HANDSHAKING:
            # start handshake
            messenger = self.messenger
            messenger.handshake(session_key=None)
        elif current == SessionState.RUNNING:
            # broadcast current meta & visa document to all stations
            messenger = self.messenger
            messenger.handshake_success()

    # Override
    def pause_state(self, state: SessionState, ctx: StateMachine):
        pass

    # Override
    def resume_state(self, state: SessionState, ctx: StateMachine):
        # TODO: clear session key for re-login?
        pass
