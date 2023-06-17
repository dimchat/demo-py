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
from typing import Set, List

from dimsdk import EntityType, ID, EVERYONE
from dimsdk import Station
from dimsdk import ReliableMessage

from ..utils import Singleton, Log, Logging
from ..common import StationInfo

from .cpu import AnsCommandProcessor
from .dispatcher import Dispatcher
from .session_center import SessionCenter


@Singleton
class BroadcastRecipientManager(Logging):

    def __init__(self):
        super().__init__()
        self.__lock = threading.Lock()
        self.__expires = 0
        self.__neighbors = set()
        self.__bots = set()

    @property
    def station_bots(self) -> Set[ID]:
        """ get station bots """
        return self.__bots

    @station_bots.setter
    def station_bots(self, bots: Set[ID]):
        """ set station bots to receive message for 'everyone@everywhere' """
        assert isinstance(bots, Set), 'bots error: %s' % bots
        self.__bots = bots

    @property
    def proactive_neighbors(self) -> Set[ID]:
        """ get neighbor stations connected to current station """
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
    def all_stations(self) -> List[StationInfo]:
        """ get stations from database """
        dispatcher = Dispatcher()
        db = dispatcher.sdb
        # TODO: get chosen provider
        providers = db.all_providers()
        assert len(providers) > 0, 'service provider not found'
        gsp = providers[0].identifier
        return db.all_stations(provider=gsp)

    @property
    def all_neighbors(self) -> Set[ID]:
        """ get all stations """
        neighbors = set()
        # get stations from chosen provider
        stations = self.all_stations
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
            self.info(msg='forward to neighbors: %s' % receiver)
            # get neighbor stations
            neighbors = self.all_neighbors
            for sid in neighbors:
                if sid in traces:  # or sid == station:
                    self.warning(msg='ignore duplicated neighbor: %s' % sid)
                    continue
                recipients.add(sid)
            # get station bots
            if receiver == EVERYONE:
                # include station bots as 'everyone@everywhere'
                bots = self.station_bots
                for bid in bots:
                    if bid in traces:
                        self.warning(msg='ignore duplicated bot: %s' % bid)
                        continue
                    recipients.add(bid)
        elif receiver.is_user:
            # 'archivist@anywhere', 'apns@anywhere'
            name = receiver.name
            if name is not None:
                assert name != 'station' and name != 'anyone', 'receiver error: %s' % receiver
                bot = AnsCommandProcessor.ans_id(name=name)
                self.info(msg='forward to bot: %s -> %s' % (name, bot))
                if bot is not None and bot not in traces:
                    recipients.add(bot)
        self.info(msg='recipients: %s -> %s' % (receiver, recipients))
        return recipients


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
            Log.warning(msg='current station should not exists here: %s, %s' % (target, recipients))
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
