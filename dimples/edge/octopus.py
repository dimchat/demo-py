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
    Octopus
    ~~~~~~~

    Edges for neighbor stations
"""

import threading
import weakref
from abc import ABC, abstractmethod
from typing import Optional, List, Set

from dimsdk import ID
from dimsdk import ReliableMessage

from ..utils import Logging
from ..utils import Runner
from ..utils import get_msg_sig
from ..common import SessionDBI

from ..client import ClientMessenger
from ..client import Terminal


class Octopus(Runner, Logging, ABC):

    def __init__(self, database: SessionDBI, local_host: str = '127.0.0.1', local_port: int = 9394):
        super().__init__(interval=60)
        self.__database = database
        self.__host = local_host
        self.__port = local_port
        self.__inner: Optional[Terminal] = None
        self.__inner_lock = threading.Lock()
        self.__outers: Set[Terminal] = set()
        self.__outer_map = weakref.WeakValueDictionary()
        self.__outer_lock = threading.Lock()

    @property
    def database(self) -> SessionDBI:
        return self.__database

    @property
    async def inner_messenger(self) -> ClientMessenger:
        with self.__inner_lock:
            terminal = self.__inner
            if terminal is None:
                terminal = await self.create_inner_terminal(host=self.__host, port=self.__port)
                self.__inner = terminal
        return terminal.messenger

    def get_outer_messenger(self, identifier: ID) -> Optional[ClientMessenger]:
        with self.__outer_lock:
            terminal = self.__outer_map.get(identifier)
        if terminal is not None:
            return terminal.messenger

    @abstractmethod
    async def create_inner_terminal(self, host: str, port: int) -> Terminal:
        raise NotImplemented

    @abstractmethod
    async def create_outer_terminal(self, host: str, port: int) -> Terminal:
        raise NotImplemented

    def add_index(self, identifier: ID, terminal: Terminal):
        with self.__outer_lock:
            # self.__outers.add(terminal)
            self.__outer_map[identifier] = terminal

    async def connect(self, host: str, port: int = 9394):
        # create a new terminal for remote host:port
        with self.__outer_lock:
            # check exist terminals
            outers = self.__outers.copy()
            for out in outers:
                # check station
                station = out.session.station
                if port == station.port and host == station.host:
                    self.warning(msg='connection already exists: (%s, %d)' % (host, port))
                    # self.__outers.discard(out)
                    return None
            # create new terminal
            terminal = await self.create_outer_terminal(host=host, port=port)
            self.__outers.add(terminal)
            return terminal

    # Override
    async def stop(self):
        # 1. stop inner terminal
        inner = self.__inner
        if inner is not None:
            await inner.stop()
        # 2. stop outer terminals
        with self.__outer_lock:
            outers = set(self.__outers)
        for out in outers:
            await out.stop()
        # 3. stop runner
        await super().stop()

    # Override
    async def setup(self):
        await super().setup()
        self.debug(msg='connecting inner station ...')
        await self.inner_messenger

    # Override
    async def process(self) -> bool:
        # get all neighbor stations
        db = self.database
        providers = await db.all_providers()
        assert len(providers) > 0, 'service provider not found'
        gsp = providers[0].identifier
        neighbors = await db.all_stations(provider=gsp)
        if neighbors is None:
            neighbors = []
        else:
            neighbors = neighbors.copy()
        # get all outer terminals
        with self.__outer_lock:
            outers = set(self.__outers)
        self.debug(msg='checking %d client(s) with %d neighbor(s)' % (len(outers), len(neighbors)))
        for out in outers:
            # check station
            station = out.session.station
            sid = station.identifier
            host = station.host
            port = station.port
            # reduce neighbors
            for item in neighbors:
                if item.port == port and item.host == host:
                    # got
                    neighbors.remove(item)
                    break
            # check outer client
            if out.running:
                # skip running client
                continue
            else:
                # remove dead client
                self.warning(msg='client stopped, remove it: %s (%s:%d)' % (sid, host, port))
            with self.__outer_lock:
                self.__outers.discard(out)
                if sid is not None:
                    self.__outer_map.pop(sid, None)
        # check new neighbors
        for item in neighbors:
            host = item.host
            port = item.port
            self.debug(msg='connecting neighbor station (%s:%d), client count: %d' % (host, port, len(self.__outers)))
            await self.connect(host=host, port=port)
        return False

    async def income_message(self, msg: ReliableMessage, priority: int = 0) -> List[ReliableMessage]:
        """ redirect message from remote station """
        sender = msg.sender
        receiver = msg.receiver
        sig = get_msg_sig(msg=msg)
        messenger = await self.inner_messenger
        if await messenger.send_reliable_message(msg=msg, priority=priority):
            self.info(msg='redirected msg (%s): %s -> %s' % (sig, sender, receiver))
        else:
            self.error(msg='failed to redirect msg (%s): %s -> %s' % (sig, sender, receiver))
        # no need to respond receipt for station
        return []

    async def outgo_message(self, msg: ReliableMessage, priority: int = 0) -> List[ReliableMessage]:
        """ redirect message to remote station """
        receiver = msg.receiver
        # get neighbor stations
        neighbor = ID.parse(identifier=msg.get('neighbor'))
        if neighbor is not None:
            neighbors = set()
            neighbors.add(neighbor)
            msg.pop('neighbor', None)
        else:
            with self.__outer_lock:
                neighbors = set(self.__outer_map.keys())
        #
        #  0. check recipients
        #
        new_recipients = set()
        old_recipients = msg.get('recipients')
        old_recipients = [] if old_recipients is None else ID.convert(array=old_recipients)
        for item in neighbors:
            if item in old_recipients:
                self.info(msg='skip exists station: %s' % item)
                continue
            self.info(msg='new neighbor station: %s' % item)
            new_recipients.add(item)
        # update 'recipients' to avoid the new recipients redirect it to same targets
        self.info(msg='append new recipients: %s, %s + %s' % (receiver, new_recipients, old_recipients))
        all_recipients = list(old_recipients) + list(new_recipients)
        msg['recipients'] = ID.revert(identifiers=all_recipients)
        #
        #  1. send to the new recipients (neighbor stations)
        #
        sig = get_msg_sig(msg=msg)
        failed_neighbors = []
        for target in new_recipients:
            messenger = self.get_outer_messenger(identifier=target)
            if messenger is None:
                # target station not my neighbor
                self.warning(msg='not my neighbor: %s (%s)' % (target, receiver))
                failed_neighbors.append(target)
            elif await messenger.send_reliable_message(msg=msg, priority=priority):
                self.info(msg='redirected msg (%s) to neighbor: %s (%s)' % (sig, target, receiver))
            else:
                self.error(msg='failed to send to neighbor: %s (%s)' % (target, receiver))
                failed_neighbors.append(target)
        if len(failed_neighbors) > 0:
            self.error(msg='failed to redirect msg (%s) for receiver (%s): %s' % (sig, receiver, failed_neighbors))
        return []
