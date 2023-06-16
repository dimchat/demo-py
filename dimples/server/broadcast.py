# -*- coding: utf-8 -*-
#
#   DIM-SDK : Decentralized Instant Messaging Software Development Kit
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

"""
    Broadcast Recipient Manager
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~
"""

import threading
import time
from typing import Optional, Set

from dimsdk import EntityType, ID, EVERYONE
from dimsdk import Station
from dimsdk import ReliableMessage

from ..utils import Singleton, Log
from ..common import SessionDBI

from .dispatcher import Dispatcher
from .session_center import SessionCenter


@Singleton
class BroadcastRecipientManager:

    def __init__(self):
        super().__init__()
        self.__neighbors = set()
        self.__expires = 0
        self.__lock = threading.Lock()
        self.__sdb: Optional[SessionDBI] = None

    @property
    def database(self) -> SessionDBI:
        return self.__sdb

    @database.setter
    def database(self, sdb: SessionDBI):
        self.__sdb = sdb

    @property
    def proactive_neighbors(self) -> Set[ID]:
        now = time.time()
        with self.__lock:
            if self.__expires < now:
                neighbors = set()
                center = SessionCenter()
                all_users = center.all_users()
                for item in all_users:
                    if item.type == EntityType.STATION:
                        neighbors.add(item)
                self.__neighbors = neighbors
                self.__expires = now + 128
            return self.__neighbors

    @property
    def all_neighbors(self) -> Set[ID]:
        neighbors = set()
        db = self.__sdb
        providers = db.all_providers()
        assert len(providers) > 0, 'service provider not found'
        gsp = providers[0].identifier
        stations = db.all_stations(provider=gsp)
        for item in stations:
            sid = item.identifier
            if sid is None or sid.is_broadcast:
                continue
            neighbors.add(sid)
        # get neighbor station from session server
        proactive_neighbors = self.proactive_neighbors
        for sid in proactive_neighbors:
            if sid is None or sid.is_broadcast:
                assert False, 'neighbor station ID error: %s' % sid
                # continue
            neighbors.add(sid)
        return neighbors

    def get_recipients(self, msg: ReliableMessage, receiver: ID) -> Set[ID]:
        recipients = set()
        # get nodes passed through, includes current node which is just added before
        traces = msg.get('traces')
        if traces is None:
            traces = []
        # if this message is sending to 'stations@everywhere' or 'everyone@everywhere'
        # get all neighbor stations to broadcast, but
        # traced nodes should be ignored to avoid cycled delivering
        if receiver == Station.EVERY or receiver == EVERYONE:
            Log.info(msg='forward to neighbors: %s' % receiver)
            # get neighbor stations
            neighbors = self.all_neighbors
            for sid in neighbors:
                if sid in traces:  # or sid == station:
                    Log.warning(msg='ignore neighbor: %s' % sid)
                    continue
                recipients.add(sid)
            # get archivist bot
            if receiver == EVERYONE:
                # include 'archivist' as 'everyone@everywhere'
                bot = ans_id(name='archivist')
                if bot is not None and bot not in traces:
                    recipients.add(bot)
        elif receiver == 'archivist@anywhere':  # or receiver == 'archivists@everywhere':
            Log.info(msg='forward to archivist: %s' % receiver)
            # get archivist bot for search command
            bot = ans_id(name='archivist')
            if bot is not None and bot not in traces:
                recipients.add(bot)
        elif receiver == 'apns@anywhere':
            Log.info(msg='forward to APNs bot: %s' % receiver)
            # get APNs bot for apns command
            bot = ans_id(name='apns')
            if bot is not None and bot not in traces:
                recipients.add(bot)
        Log.info(msg='recipients: %s -> %s' % (receiver, recipients))
        return recipients


def ans_id(name: str) -> Optional[ID]:
    try:
        return ID.parse(identifier=name)
    except ValueError as e:
        Log.warning(msg='ANS record not exists: %s, %s' % (name, e))


def broadcast_reliable_message(msg: ReliableMessage, station: ID):
    receiver = msg.receiver
    # get other recipients for broadcast message
    manager = BroadcastRecipientManager()
    recipients = manager.get_recipients(msg=msg, receiver=receiver)
    if len(recipients) == 0:
        Log.warning('other recipients not found: %s' % receiver)
        return 0
    sender = msg.sender
    # dispatch
    dispatcher = Dispatcher()
    for target in recipients:
        assert not target.is_broadcast, 'recipient error: %s, %s' % (target, receiver)
        if target == station:
            Log.error(msg='current station should not exists here: %s, %s' % (target, recipients))
            continue
        elif target == sender:
            Log.warning(msg='skip sender: %s, %s' % (target, recipients))
            continue
        dispatcher.deliver_message(msg=msg, receiver=target)

        # TODO: after deliver to connected neighbors, the dispatcher will continue
        #       delivering via station bridge, should we mark 'sent_neighbors' in
        #       only one message to the bridge, let the bridge to separate for other
        #       neighbors which not connect to this station directly?
    # OK
    Log.info(msg='Broadcast message delivered: %s, sender: %s' % (recipients, sender))
    return len(recipients)
