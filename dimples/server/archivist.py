# -*- coding: utf-8 -*-
#
#   DIM-SDK : Decentralized Instant Messaging Software Development Kit
#
#                                Written in 2023 by Moky <albert.moky@gmail.com>
#
# ==============================================================================
# MIT License
#
# Copyright (c) 2023 Albert Moky
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
from abc import ABC
from typing import Dict, List, Set

from dimsdk import DateTime
from dimsdk import FrequencyChecker
from dimsdk import EntityType, ID, Document
from dimsdk import Envelope, InstantMessage
from dimsdk import Command, MetaCommand, DocumentCommand
from dimsdk import Station

from ..common import AccountDBI
from ..common import CommonArchivist
from ..common import CommonFacebook, CommonMessenger
from ..common import StationInfo

from .session_center import SessionCenter


def get_facebook(archivist: CommonArchivist):
    facebook = archivist.facebook
    if facebook is not None:
        assert isinstance(facebook, CommonFacebook), 'facebook error: %s' % facebook
    return facebook


def get_messenger(archivist: CommonArchivist):
    messenger = archivist.messenger
    if messenger is not None:
        assert isinstance(messenger, CommonMessenger), 'messenger error: %s' % messenger
    return messenger


def get_dispatcher():
    from .dispatcher import Dispatcher
    return Dispatcher()


class ServerArchivist(CommonArchivist, ABC):

    # each respond will be expired after 10 minutes
    RESPOND_EXPIRES = 600.0  # seconds

    def __init__(self, database: AccountDBI):
        super().__init__(database=database)
        self.__document_responses = FrequencyChecker(expires=self.RESPOND_EXPIRES)
        self.__last_active_members: Dict[ID, ID] = {}  # group => member
        # neighbor stations
        self.__neighbors = set()
        self.__lock = threading.Lock()
        self.__expires = 0

    @property
    def active_stations(self) -> Set[ID]:
        """ get neighbor stations connected to current station """
        now = DateTime.now()
        with self.__lock:
            if self.__expires < now.timestamp:
                neighbors = set()
                center = SessionCenter()
                all_users = center.all_users()
                for item in all_users:
                    if item.type == EntityType.STATION:
                        neighbors.add(item)
                self.__neighbors = neighbors
                self.__expires = now.timestamp + 128
            return self.__neighbors

    @property
    async def all_stations(self) -> List[StationInfo]:
        """ get stations from database """
        dispatcher = get_dispatcher()
        db = dispatcher.sdb
        # TODO: get chosen provider
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
        facebook = get_facebook(archivist=self)
        messenger = get_messenger(archivist=self)
        if facebook is None or messenger is None:
            self.error(msg='twins not ready yet: %s, %s' % (facebook, messenger))
            return False
        sid = facebook.current_user.identifier
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
        # r_msg['recipients'] = ID.revert(neighbors)
        for receiver in neighbors:
            if receiver == sid:
                self.debug(msg='skip cycled message: %s -> %s' % (sid, receiver))
                continue
            await dispatcher.deliver_message(msg=r_msg, receiver=receiver)
        return len(neighbors) > 0

    # protected
    def is_documents_respond_expired(self, identifier: ID, force: bool) -> bool:
        return self.__document_responses.is_expired(key=identifier, force=force)

    def set_last_active_member(self, member: ID, group: ID):
        self.__last_active_members[group] = member

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
        if not self.is_documents_query_expired(identifier=identifier):
            # query not expired yet
            self.info(msg='document query not expired yet: %s' % identifier)
            return False
        last_time = await self.get_last_document_time(identifier=identifier, documents=documents)
        self.info(msg='querying document for: %s, last time: %s' % (identifier, last_time))
        command = DocumentCommand.query(identifier=identifier, last_time=last_time)
        return await self._broadcast_command(command=command)

    # Override
    async def query_members(self, group: ID, members: List[ID]) -> bool:
        # station will never process group info
        self.error(msg='DON\'t call me!')
        return False
