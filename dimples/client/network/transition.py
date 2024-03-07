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

from startrek import DockerStatus

from .state import StateMachine, StateTransition
from .state import StateOrder


class TransitionBuilder:

    # noinspection PyMethodMayBeStatic
    def get_default_connecting_transition(self):
        return DefaultConnectingTransition(target=StateOrder.CONNECTING)

    # Connecting

    # noinspection PyMethodMayBeStatic
    def get_connecting_connected_transition(self):
        return ConnectingConnectedTransition(target=StateOrder.CONNECTED)

    # noinspection PyMethodMayBeStatic
    def get_connecting_error_transition(self):
        return ConnectingErrorTransition(target=StateOrder.ERROR)

    # Connected

    # noinspection PyMethodMayBeStatic
    def get_connected_handshaking_transition(self):
        return ConnectedHandshakingTransition(target=StateOrder.HANDSHAKING)

    # noinspection PyMethodMayBeStatic
    def get_connected_error_transition(self):
        return ConnectedErrorTransition(target=StateOrder.ERROR)

    # Handshaking

    # noinspection PyMethodMayBeStatic
    def get_handshaking_running_transition(self):
        return HandshakingRunningTransition(target=StateOrder.RUNNING)

    # noinspection PyMethodMayBeStatic
    def get_handshaking_connected_transition(self):
        return HandshakingConnectedTransition(target=StateOrder.CONNECTED)

    # noinspection PyMethodMayBeStatic
    def get_handshaking_error_transition(self):
        return HandshakingErrorTransition(target=StateOrder.ERROR)

    # Running

    # noinspection PyMethodMayBeStatic
    def get_running_default_transition(self):
        return RunningDefaultTransition(target=StateOrder.INIT)

    # noinspection PyMethodMayBeStatic
    def get_running_error_transition(self):
        return RunningErrorTransition(target=StateOrder.ERROR)

    # Error

    # noinspection PyMethodMayBeStatic
    def get_error_default_transition(self):
        return ErrorDefaultTransition(target=StateOrder.INIT)


#
#   Transitions
#

class DefaultConnectingTransition(StateTransition):
    """
        Default -> Connecting
        ~~~~~~~~~~~~~~~~~~~~~
        When the session ID was set, and connection is building.

        The session key must be empty now, it will be set
        after handshake success.
    """

    # Override
    def evaluate(self, ctx: StateMachine, now: float) -> bool:
        # assert ctx.session_key is None, 'session key must be empty before handshaking'
        if ctx.session_id is None:
            # current user not set yet
            return False
        return ctx.status in [DockerStatus.PREPARING, DockerStatus.READY]


class ConnectingConnectedTransition(StateTransition):
    """
        Connecting -> Connected
        ~~~~~~~~~~~~~~~~~~~~~~~
        When connection built.

        The session ID must be set, and the session key must be empty now.
    """

    # Override
    def evaluate(self, ctx: StateMachine, now: float) -> bool:
        # assert ctx.session_key is None, 'session key must be empty before handshaking'
        # assert ctx.session_id is not None, 'current user lost?'
        return ctx.status == DockerStatus.READY


class ConnectingErrorTransition(StateTransition):
    """
        Connecting -> Error
        ~~~~~~~~~~~~~~~~~~~
        When connection lost.

        The session ID must be set, and the session key must be empty now.
    """

    # Override
    def evaluate(self, ctx: StateMachine, now: float) -> bool:
        # assert ctx.session_key is None, 'session key must be empty before handshaking'
        # assert ctx.session_id is not None, 'current user lost?'
        if self.is_expired(state=ctx.current_state, now=now):
            # connecting expired, do it again
            return True
        return ctx.status not in [DockerStatus.PREPARING, DockerStatus.READY]


class ConnectedHandshakingTransition(StateTransition):
    """
        Connected -> Handshaking
        ~~~~~~~~~~~~~~~~~~~~~~~~
        Do handshaking immediately after connected.

        The session ID must be set, and the session key must be empty now.
    """

    # Override
    def evaluate(self, ctx: StateMachine, now: float) -> bool:
        if ctx.session_id is None:
            # FIXME: current user lost?
            #        state will be changed to 'error'
            return False
        return ctx.status == DockerStatus.READY


class ConnectedErrorTransition(StateTransition):
    """
        Connected -> Error
        ~~~~~~~~~~~~~~~~~~
        When connection lost.

        The session ID must be set, and the session key must be empty now.
    """

    # Override
    def evaluate(self, ctx: StateMachine, now: float) -> bool:
        if ctx.session_id is None:
            # FIXME: current user lost?
            return True
        return ctx.status != DockerStatus.READY


class HandshakingRunningTransition(StateTransition):
    """
        Handshaking -> Running
        ~~~~~~~~~~~~~~~~~~~~~~
        When session key was set (handshake success).

        The session ID must be set.
    """

    # Override
    def evaluate(self, ctx: StateMachine, now: float) -> bool:
        if ctx.session_id is None:
            # FIXME: current user lost?
            #        state will be changed to 'error'
            return False
        if ctx.status != DockerStatus.READY:
            # connection lost, state will be changed to 'error'
            return False
        # when current user changed, the session key will cleared, so
        # if it's set again, it means handshake success
        return ctx.session_key is not None


class HandshakingConnectedTransition(StateTransition):
    """
        Handshaking -> Connected
        ~~~~~~~~~~~~~~~~~~~~~~~~
        When handshaking expired.

        The session ID must be set, and the session key must be empty now.
    """

    # Override
    def evaluate(self, ctx: StateMachine, now: float) -> bool:
        if ctx.session_id is None:
            # FIXME: current user lost?
            #        state will be changed to 'error'
            return False
        if ctx.status != DockerStatus.READY:
            # connection lost, state will be changed to 'error'
            return False
        if ctx.session_key is not None:
            # session key was set, state will be changed to 'running'
            return False
        # handshake expired, do it again
        return self.is_expired(state=ctx.current_state, now=now)


class HandshakingErrorTransition(StateTransition):
    """
        Handshaking -> Error
        ~~~~~~~~~~~~~~~~~~~~
        When connection lost.

        The session ID must be set, and the session key must be empty now.
    """

    # Override
    def evaluate(self, ctx: StateMachine, now: float) -> bool:
        if ctx.session_id is None:
            # FIXME: current user lost?
            return True
        return ctx.status != DockerStatus.READY


class RunningDefaultTransition(StateTransition):
    """
        Running -> Default
        ~~~~~~~~~~~~~~~~~~
        When session id or session key was erased.

        If session id was erased, it means user logout, the session key
        must be removed at the same time;
        If only session key was erased, but the session id kept the same,
        it means force the user login again.
    """

    # Override
    def evaluate(self, ctx: StateMachine, now: float) -> bool:
        if ctx.status != DockerStatus.READY:
            # connection lost, state will be changed to 'error'
            return False
        if ctx.session_id is None:
            # user logout / switched?
            return True
        # force user login again?
        return ctx.session_key is None


class RunningErrorTransition(StateTransition):
    """
        Running -> Error
        ~~~~~~~~~~~~~~~~
        When connection lost.
    """

    # Override
    def evaluate(self, ctx: StateMachine, now: float) -> bool:
        return ctx.status != DockerStatus.READY


class ErrorDefaultTransition(StateTransition):
    """
        Error -> Default
        ~~~~~~~~~~~~~~~~
        When connection reset.
    """

    # Override
    def evaluate(self, ctx: StateMachine, now: float) -> bool:
        return ctx.status != DockerStatus.ERROR
