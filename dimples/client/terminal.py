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

from abc import ABC, abstractmethod
from typing import Optional

from startrek.skywalker import Daemon

from dimsdk import DateTime
from dimsdk import EntityType
from dimsdk import Station
from dimsdk import Packer, Processor

from ..utils import Logging
from ..utils import Runner
from ..utils import StateDelegate

from ..common import SessionDBI

from .network import ClientSession
from .network import StateMachine, SessionState
from .network.state import StateOrder

from .facebook import ClientFacebook
from .messenger import ClientMessenger
from .packer import ClientMessagePacker
from .processor import ClientMessageProcessor


class DeviceMixin:

    @property
    def user_agent(self) -> str:
        return 'DIMP/1.0 (Client; Linux; en-US)' \
               ' DIMCoreKit/1.0 (Terminal) DIM-by-MOKY/1.0'


class Terminal(Runner, DeviceMixin, Logging, StateDelegate, ABC):

    def __init__(self, facebook: ClientFacebook, database: SessionDBI):
        super().__init__(interval=16.0)
        self.__sdb = database
        self.__facebook = facebook
        self.__messenger = None
        # default online time
        self.__last_time = 0
        self.__daemon = Daemon(target=self)

    @property
    def database(self) -> SessionDBI:
        return self.__sdb

    @property
    def facebook(self) -> ClientFacebook:
        return self.__facebook

    @property
    def messenger(self) -> Optional[ClientMessenger]:
        return self.__messenger

    @property
    def session(self) -> Optional[ClientSession]:
        messenger = self.messenger
        if messenger is not None:
            return messenger.session

    #
    #   Connection
    #

    async def connect(self, host: str, port: int) -> ClientMessenger:
        #
        #  0. check old session
        #
        old = self.messenger
        if old is not None:
            session = old.session
            if session.active:
                # current session is active
                station = session.station
                if station.port == port and station.host == host:
                    # same target
                    self.warning(msg='active session connected to %s:%d .' % (host, port))
                    return old
            await session.stop()
            self.__messenger = None
        self.info(msg='connecting to %s:%d ...' % (host, port))
        facebook = self.facebook
        #
        #  1. create new session with station
        #
        station = self._create_station(host=host, port=port)
        session = self._create_session(station=station)
        #
        #  2. create new messenger with session
        #
        messenger = self._create_messenger(facebook=facebook, session=session)
        self.__messenger = messenger
        # set weak reference to messenger
        session.messenger = messenger  # weak reference
        #
        #  3. create packer, processor for messenger
        #     they have weak references to facebook & messenger
        #
        messenger.packer = self._create_packer(facebook=facebook, messenger=messenger)
        messenger.processor = self._create_processor(facebook=facebook, messenger=messenger)
        #
        #  4. login with current user
        #
        user = await self.facebook.current_user
        assert user is not None, 'failed to get current user'
        session.set_identifier(identifier=user.identifier)
        return messenger

    def _create_station(self, host: str, port: int) -> Station:
        station = Station(host=host, port=port)
        station.data_source = self.facebook
        return station

    def _create_session(self, station: Station) -> ClientSession:
        session = ClientSession(station=station, database=self.database)
        session.start(delegate=self)
        return session

    # noinspection PyMethodMayBeStatic
    def _create_packer(self, facebook: ClientFacebook, messenger: ClientMessenger) -> Packer:
        return ClientMessagePacker(facebook=facebook, messenger=messenger)

    # noinspection PyMethodMayBeStatic
    def _create_processor(self, facebook: ClientFacebook, messenger: ClientMessenger) -> Processor:
        return ClientMessageProcessor(facebook=facebook, messenger=messenger)

    @abstractmethod
    def _create_messenger(self, facebook: ClientFacebook, session: ClientSession) -> ClientMessenger:
        raise NotImplemented

    #
    #   Threading
    #

    async def start(self):
        if self.running:
            await self.stop()
            # await self._idle()
        # start an async task in background
        self.__daemon.start()

    # @property  # Override
    # def running(self) -> bool:
    #     if super().running:
    #         return self.session.running

    # Override
    async def finish(self):
        # stop session in messenger
        messenger = self.messenger
        if messenger is not None:
            self.__messenger = None
            session = messenger.session
            await session.stop()
        # stop the terminal
        await super().finish()

    # Override
    async def process(self) -> bool:
        #
        #  1. check connection
        #
        session = self.session
        state = None if session is None else session.state
        index = -1 if state is None else state.index
        if index != StateOrder.RUNNING:
            # handshake not accepted
            return False
        elif not session.ready:
            # session not ready
            return False
        #
        #  2. check timeout
        #
        now = DateTime.current_timestamp()
        if self._needs_keep_online(last=self.__last_time, now=now):
            # update last online time
            self.__last_time = now
        else:
            # not expired yet
            return False
        #
        #  3. try to report every 5 minutes to keep user online
        #
        try:
            await self._keep_online()
        except Exception as error:
            self.error(msg='Terminal error: %s' % error)
        return False

    # noinspection PyMethodMayBeStatic
    def _needs_keep_online(self, last: float, now: float) -> bool:
        if last <= 8:
            # not login yet
            return False
        # keep online every 5 minutes
        return last + 300 < now

    async def _keep_online(self):
        facebook = self.facebook
        messenger = self.messenger
        user = await facebook.current_user
        if user is None or messenger is None:
            return False
        elif user.type == EntityType.STATION:
            # a station won't login to another station, if here is a station,
            # it must be a station bridge for roaming messages, we just send
            # report command to the target station to keep session online.
            await messenger.report_online(sender=user.identifier)
        else:
            # send login command to everyone to provide more information.
            # this command can keep the user online too.
            await messenger.broadcast_login(sender=user.identifier, user_agent=self.user_agent)

    #
    #   StateDelegate
    #

    # Override
    async def enter_state(self, state: SessionState, ctx: StateMachine, now: float):
        # called before state changed
        session = self.session
        station = session.station
        self.info(msg='enter state: %s, %s => %s' % (state, session.identifier, station.identifier))

    # Override
    async def exit_state(self, state: SessionState, ctx: StateMachine, now: float):
        # called after state changed
        current = ctx.current_state
        self.info(msg='server state changed: %s -> %s, %s' % (state, current, self.session.station))
        index = current.index if isinstance(current, SessionState) else -1
        if index == -1 or index == StateOrder.ERROR:
            self.__last_time = 0
            return
        elif index == StateOrder.INIT or index == StateOrder.CONNECTING:
            # check current user
            user = ctx.session_id
            if user is None:
                self.warning(msg='current user not set')
                return
            self.info(msg='connect for user: %s' % user)
            session = self.session
            remote = None if session is None else session.remote_address
            if remote is None:
                self.warning(msg='failed to get remote address: %s' % session)
                return
            docker = await session.gate.fetch_porter(remote=remote, local=None)
            if docker is None:
                self.error(msg='failed to connect: %s' % str(remote))
            else:
                self.info(msg='connected to remote: %s' % str(remote))
        elif index == StateOrder.HANDSHAKING:
            # start handshake
            messenger = self.messenger
            if messenger is not None:
                await messenger.handshake(session_key=None)
        elif index == StateOrder.RUNNING:
            # broadcast current meta & visa document to all stations
            messenger = self.messenger
            if messenger is not None:
                await messenger.handshake_success()
            # update last online time
            self.__last_time = now

    # Override
    async def pause_state(self, state: SessionState, ctx: StateMachine, now: float):
        pass

    # Override
    async def resume_state(self, state: SessionState, ctx: StateMachine, now: float):
        # TODO: clear session key for re-login?
        pass
