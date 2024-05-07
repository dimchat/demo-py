# -*- coding: utf-8 -*-
# ==============================================================================
# MIT License
#
# Copyright (c) 2021 Albert Moky
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

import asyncio
import weakref
from abc import ABC
from enum import IntEnum
from typing import Optional, Union

from dimsdk import ID

from startrek.fsm import Runner
from startrek.fsm import Context, BaseTransition, BaseState, AutoMachine
from startrek import Docker, DockerStatus

# from .session import ClientSession


class StateMachine(AutoMachine, Context):

    def __init__(self, session):
        super().__init__()
        self.__session = weakref.ref(session)
        self.__docker_ref = None
        # init states
        builder = self._create_state_builder()
        self.add_state(state=builder.get_default_state())
        self.add_state(state=builder.get_connecting_state())
        self.add_state(state=builder.get_connected_state())
        self.add_state(state=builder.get_handshaking_state())
        self.add_state(state=builder.get_running_state())
        self.add_state(state=builder.get_error_state())

    @property
    def session(self):  # -> ClientSession:
        return self.__session()

    @property
    def docker(self) -> Optional[Docker]:
        ref = self.__docker_ref
        if ref is not None:
            return ref()

    @docker.setter
    def docker(self, worker: Docker):
        if worker is None:
            self.__docker_ref = None
        else:
            self.__docker_ref = weakref.ref(worker)

    # noinspection PyMethodMayBeStatic
    def _create_state_builder(self):
        from .transition import TransitionBuilder
        return StateBuilder(transition_builder=TransitionBuilder())

    @property  # Override
    def context(self) -> Context:
        return self

    @property
    def session_key(self) -> Optional[str]:
        session = self.session
        return session.key

    @property
    def session_id(self) -> ID:
        session = self.session
        return session.identifier

    @property
    def status(self) -> DockerStatus:
        docker = self.docker
        if docker is not None:
            return docker.status
        else:
            session = self.session
            gate = session.gate
            task = Runner.async_run(coro=gate.fetch_docker([], remote=session.remote_address, local=None))
            task.add_done_callback(self._fetch_docker_callback)
        # waiting for callback
        return DockerStatus.ERROR

    def _fetch_docker_callback(self, t: asyncio.Task):
        self.docker = t.result()


class StateOrder(IntEnum):
    """ Connection State Order """
    INIT = 0  # default
    CONNECTING = 1
    CONNECTED = 2
    HANDSHAKING = 3
    RUNNING = 4
    ERROR = 5


# noinspection PyAbstractClass
class StateTransition(BaseTransition[StateMachine], ABC):

    def __init__(self, target: Union[int, StateOrder]):
        if isinstance(target, StateOrder):
            target = target.value
        super().__init__(target=target)

    # noinspection PyMethodMayBeStatic
    def is_expired(self, state, now: float) -> bool:
        assert isinstance(state, SessionState), 'state error: %s' % state
        return 0 < state.enter_time < (now - 30)


class SessionState(BaseState[StateMachine, StateTransition]):
    """
        Session State
        ~~~~~~~~~~~~~

        Defined for indicating session states

            DEFAULT     - initialized
            CONNECTING  - connecting to station
            CONNECTED   - connected to station
            HANDSHAKING - trying to log in
            RUNNING     - handshake accepted
            ERROR       - network error
    """

    def __init__(self, order: StateOrder):
        super().__init__(index=order.value)
        self.__name = str(order)
        self.__time: float = 0  # enter time

    @property
    def name(self) -> str:
        return self.__name

    @property
    def enter_time(self) -> float:
        return self.__time

    # Override
    def __str__(self) -> str:
        return self.__name

    # Override
    def __repr__(self) -> str:
        return self.__name

    # Override
    def __eq__(self, other) -> bool:
        if isinstance(other, SessionState):
            if self is other:
                return True
            return self.index == other.index
        elif isinstance(other, StateOrder):
            return self.index == other.value
        elif isinstance(other, int):
            return self.index == other
        elif isinstance(other, str):
            return self.__name == other
        else:
            return False

    # Override
    def __ne__(self, other) -> bool:
        if isinstance(other, SessionState):
            if self is other:
                return False
            return self.index != other.index
        elif isinstance(other, StateOrder):
            return self.index != other.value
        elif isinstance(other, int):
            return self.index != other
        elif isinstance(other, str):
            return self.__name != other
        else:
            return True

    # Override
    async def on_enter(self, old, ctx: StateMachine, now: float):
        self.__time = now

    # Override
    async def on_exit(self, new, ctx: StateMachine, now: float):
        self.__time = 0

    # Override
    async def on_pause(self, ctx: StateMachine, now: float):
        pass

    # Override
    async def on_resume(self, ctx: StateMachine, now: float):
        pass


#
#   Builders
#

class StateBuilder:

    def __init__(self, transition_builder):
        super().__init__()
        self.__builder = transition_builder

    def get_default_state(self) -> SessionState:
        builder = self.__builder
        # assert isinstance(builder, TransitionBuilder)
        state = SessionState(order=StateOrder.INIT)
        # Default -> Connecting
        state.add_transition(transition=builder.get_default_connecting_transition())
        return state

    def get_connecting_state(self) -> SessionState:
        builder = self.__builder
        # assert isinstance(builder, TransitionBuilder)
        state = SessionState(order=StateOrder.CONNECTING)
        # Connecting -> Connected
        state.add_transition(transition=builder.get_connecting_connected_transition())
        # Connecting -> Error
        state.add_transition(transition=builder.get_connecting_error_transition())
        return state

    def get_connected_state(self) -> SessionState:
        builder = self.__builder
        # assert isinstance(builder, TransitionBuilder)
        state = SessionState(order=StateOrder.CONNECTED)
        # Connected -> Handshaking
        state.add_transition(transition=builder.get_connected_handshaking_transition())
        # Connected -> Error
        state.add_transition(transition=builder.get_connected_error_transition())
        return state

    def get_handshaking_state(self) -> SessionState:
        builder = self.__builder
        # assert isinstance(builder, TransitionBuilder)
        state = SessionState(order=StateOrder.HANDSHAKING)
        # Handshaking -> Running
        state.add_transition(transition=builder.get_handshaking_running_transition())
        # Handshaking -> Connected
        state.add_transition(transition=builder.get_handshaking_connected_transition())
        # Handshaking -> Error
        state.add_transition(transition=builder.get_handshaking_error_transition())
        return state

    def get_running_state(self) -> SessionState:
        builder = self.__builder
        # assert isinstance(builder, TransitionBuilder)
        state = SessionState(order=StateOrder.RUNNING)
        # Running -> Default
        state.add_transition(transition=builder.get_running_default_transition())
        # Running -> Error
        state.add_transition(transition=builder.get_running_error_transition())
        return state

    def get_error_state(self) -> SessionState:
        builder = self.__builder
        # assert isinstance(builder, TransitionBuilder)
        state = SessionState(order=StateOrder.ERROR)
        # Error -> Default
        state.add_transition(transition=builder.get_error_default_transition())
        return state
