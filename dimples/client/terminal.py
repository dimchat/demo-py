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
import time

from dimples import EntityType

from ..utils import Runner, Logging
from ..utils import StateDelegate

from .network import ClientSession
from .network import StateMachine, SessionState

from .messenger import ClientMessenger


class Terminal(Runner, StateDelegate, Logging):

    def __init__(self, messenger: ClientMessenger):
        super().__init__(interval=60)
        self.__messenger = messenger
        # session state
        fsm = StateMachine(session=messenger.session)
        fsm.delegate = self
        self.__fsm = fsm
        # default online time
        self.__last_time = time.time()

    @property
    def user_agent(self) -> str:
        return 'DIMP/0.4 (Client; Linux; en-US) DIMCoreKit/0.9 (Terminal) DIM-by-GSP/1.0'

    @property
    def messenger(self) -> ClientMessenger:
        return self.__messenger

    @property
    def session(self) -> ClientSession:
        return self.messenger.session

    @property
    def state(self) -> SessionState:
        ss = self.__fsm.current_state
        assert ss is None or isinstance(ss, SessionState), 'session state error: %s' % ss
        return ss

    @property
    def is_alive(self) -> bool:
        # if more than 10 minutes no online command sent
        # means this terminal is dead
        now = time.time()
        return now < (self.__last_time + 600)

    # @property  # Override
    # def running(self) -> bool:
    #     if super().running:
    #         return self.is_alive

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
        now = time.time()
        if now < (self.__last_time + 300):
            # last sent within 5 minutes
            return False
        # check session state
        messenger = self.messenger
        session = messenger.session
        usr_id = session.identifier
        if usr_id is None or self.state != SessionState.RUNNING:
            # handshake not accepted
            return False
        # report every 5 minutes to keep user online
        if usr_id.type == EntityType.STATION:
            # a station won't login to another station, if here is a station,
            # it must be a station bridge for roaming messages, we just send
            # report command to the target station to keep session online.
            messenger.report_online(sender=usr_id)
        else:
            # send login command to everyone to provide more information.
            # this command can keep the user online too.
            messenger.broadcast_login(sender=usr_id, user_agent=self.user_agent)
        # update last online time
        self.__last_time = now

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
            session = messenger.session
            usr_id = session.identifier
            if usr_id is not None and usr_id.type != EntityType.STATION:
                # send login command to everyone to provide more information.
                messenger.broadcast_login(sender=usr_id, user_agent=self.user_agent)
            # update last online time
            self.__last_time = time.time()

    # Override
    def pause_state(self, state: SessionState, ctx: StateMachine):
        pass

    # Override
    def resume_state(self, state: SessionState, ctx: StateMachine):
        # TODO: clear session key for re-login?
        pass
