# -*- coding: utf-8 -*-
#
#   DIM-SDK : Decentralized Instant Messaging Software Development Kit
#
#                                Written in 2024 by Moky <albert.moky@gmail.com>
#
# ==============================================================================
# MIT License
#
# Copyright (c) 2024 Albert Moky
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

import threading
import weakref
from typing import Optional, Set, List

from dimsdk import DateTime
from dimsdk import EntityType
from dimsdk import ID, Document, Visa
from dimsdk import Command, MetaCommand, DocumentCommand
from dimsdk import Envelope, InstantMessage
from dimsdk import Station

from ..utils import Logging
from ..common import AccountDBI
from ..common import StationInfo
from ..common import EntityChecker
from ..common import CommonFacebook, CommonMessenger


def get_dispatcher():
    from .dispatcher import Dispatcher
    return Dispatcher()


def session_database():
    dispatcher = get_dispatcher()
    return dispatcher.sdb


def session_center():
    from .session_center import SessionCenter
    return SessionCenter()


class ServerChecker(EntityChecker, Logging):

    def __init__(self, database: AccountDBI, facebook: CommonFacebook):
        super().__init__(database=database)
        self.__barrack = weakref.ref(facebook)
        self.__transceiver = None
        # neighbor stations
        self.__neighbors = set()
        self.__lock = threading.Lock()
        self.__expires = 0

    @property
    def facebook(self) -> Optional[CommonFacebook]:
        return self.__barrack()

    @property
    def messenger(self) -> Optional[CommonMessenger]:
        ref = self.__transceiver
        if ref is not None:
            return ref()

    @messenger.setter
    def messenger(self, transceiver: CommonMessenger):
        self.__transceiver = None if transceiver is None else weakref.ref(transceiver)

    @property
    def active_stations(self) -> Set[ID]:
        """ get neighbor stations connected to current station """
        now = DateTime.current_timestamp()
        with self.__lock:
            if self.__expires < now:
                neighbors = set()
                center = session_center()
                all_users = center.all_users()
                for item in all_users:
                    if item.type == EntityType.STATION:
                        neighbors.add(item)
                self.__neighbors = neighbors
                self.__expires = now + 128
            return self.__neighbors

    @property
    async def all_stations(self) -> List[StationInfo]:
        """ get stations from database """
        # TODO: get chosen provider
        db = session_database()
        providers = await db.all_providers()
        assert len(providers) > 0, 'service provider not found'
        gsp = providers[0].identifier
        return await db.all_stations(provider=gsp)

    @property
    async def all_neighbors(self) -> Set[ID]:
        """ get all stations """
        neighbors = set()
        # get stations from chosen provider
        chosen_stations = await self.all_stations
        for item in chosen_stations:
            sid = item.identifier
            if sid is None or sid.is_broadcast:
                continue
            neighbors.add(sid)
        # get neighbor station from session server
        proactive_neighbors = self.active_stations
        for sid in proactive_neighbors:
            if sid is None or sid.is_broadcast:
                self.error(msg='neighbor station ID error: %s' % sid)
                continue
            neighbors.add(sid)
        return neighbors

    async def _broadcast_command(self, command: Command) -> bool:
        facebook = self.facebook
        messenger = self.messenger
        if facebook is None or messenger is None:
            self.error(msg='facebook messenger not ready yet: %s, %s' % (facebook, messenger))
            return False
        user = await facebook.current_user
        sid = user.identifier
        env = Envelope.create(sender=sid, receiver=Station.EVERY)
        i_msg = InstantMessage.create(head=env, body=command)
        # pack & deliver message
        s_msg = await messenger.encrypt_message(msg=i_msg)
        r_msg = await messenger.sign_message(msg=s_msg)
        # dispatch
        dispatcher = get_dispatcher()
        neighbors = await self.all_neighbors
        self.info(msg='broadcast command "%s" to neighbors: %s' % (command.cmd, neighbors))
        # # avoid the new recipients redirect it to same targets
        # r_msg['recipients'] = ID.revert(identifiers=neighbors)
        for receiver in neighbors:
            if receiver == sid:
                self.debug(msg='skip cycled message: %s -> %s' % (sid, receiver))
                continue
            await dispatcher.deliver_message(msg=r_msg, receiver=receiver)
        return len(neighbors) > 0

    # Override
    async def query_meta(self, identifier: ID) -> bool:
        if not self.is_meta_query_expired(identifier=identifier):
            # query not expired yet
            self.info(msg='meta query not expired yet: %s' % identifier)
            return False
        self.info(msg='querying meta for: %s' % identifier)
        command = MetaCommand.query(identifier=identifier)
        return await self._broadcast_command(command=command)

    # Override
    async def query_documents(self, identifier: ID, documents: List[Document]) -> bool:
        if not self.is_document_query_expired(identifier=identifier):
            # query not expired yet
            self.info(msg='document query not expired yet: %s' % identifier)
            return False
        last_time = self.get_last_document_time(identifier=identifier, documents=documents)
        self.info(msg='querying document for: %s, last time: %s' % (identifier, last_time))
        command = DocumentCommand.query(identifier=identifier, last_time=last_time)
        return await self._broadcast_command(command=command)

    # Override
    async def query_members(self, group: ID, members: List[ID]) -> bool:
        # station will never process group info
        self.error(msg='DON\'t call me!')
        return False

    # Override
    async def send_visa(self, visa: Visa, receiver: ID, updated: bool = False) -> bool:
        me = visa.identifier
        if me == receiver:
            self.warning(msg='skip cycled message: %s, %s' % (receiver, visa))
            return False
        messenger = self.messenger
        if messenger is None:
            self.error(msg='messenger not ready yet')
            return False
        elif not self.is_document_response_expired(identifier=receiver, force=updated):
            # response not expired yet
            self.debug(msg='visa response not expired yet: %s' % receiver)
            return False
        self.info(msg='push visa document: %s => %s' % (me, receiver))
        content = DocumentCommand.response(identifier=me, meta=None, documents=[visa])
        _, r_msg = await messenger.send_content(content=content, sender=me, receiver=receiver, priority=1)
        return r_msg is not None
