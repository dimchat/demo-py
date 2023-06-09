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
    Messenger for request handler in station
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    Transform and send message
"""

import threading
import time
from typing import Optional, Set, List

from dimsdk import EntityType, ID, EVERYONE
from dimsdk import Station
from dimsdk import Envelope, Command, MetaCommand, DocumentCommand
from dimsdk import InstantMessage
from dimsdk import SecureMessage, ReliableMessage

from ..utils import Singleton, Log, QueryFrequencyChecker
from ..common import HandshakeCommand
from ..common import CommonMessenger
from ..common import SessionDBI

from .packer import FilterManager
from .dispatcher import Dispatcher
from .session_center import SessionCenter


class ServerMessenger(CommonMessenger):

    def __broadcast_reliable_message(self, msg: ReliableMessage, station: ID):
        receiver = msg.receiver
        db = self.session.database
        # get other recipients
        recipients = get_recipients(msg=msg, receiver=receiver, db=db)
        if len(recipients) == 0:
            self.warning('other recipients not found: %s' % receiver)
            return 0
        sender = msg.sender
        # dispatch
        dispatcher = Dispatcher()
        for target in recipients:
            assert not target.is_broadcast, 'recipient error: %s, %s' % (target, receiver)
            if target == station:
                self.error(msg='current station should not exists here: %s, %s' % (target, recipients))
                continue
            elif target == sender:
                self.warning(msg='skip sender: %s, %s' % (target, recipients))
                continue
            dispatcher.deliver_message(msg=msg, receiver=target)

            # TODO: after deliver to connected neighbors, the dispatcher will continue
            #       delivering via station bridge, should we mark 'sent_neighbors' in
            #       only one message to the bridge, let the bridge to separate for other
            #       neighbors which not connect to this station directly?
        # OK
        self.info(msg='Broadcast message delivered: %s, sender: %s' % (recipients, sender))
        return len(recipients)

    def __broadcast_command(self, content: Command, receiver: ID):
        sid = self.facebook.current_user.identifier
        env = Envelope.create(sender=sid, receiver=receiver)
        i_msg = InstantMessage.create(head=env, body=content)
        # pack & deliver message
        s_msg = self.encrypt_message(msg=i_msg)
        r_msg = self.sign_message(msg=s_msg)
        self.__broadcast_reliable_message(msg=r_msg, station=sid)

    # Override
    def query_meta(self, identifier: ID) -> bool:
        checker = QueryFrequencyChecker()
        if not checker.meta_query_expired(identifier=identifier):
            # query not expired yet
            self.debug(msg='meta query not expired yet: %s' % identifier)
            return False
        self.info(msg='querying meta of %s from neighbor stations' % identifier)
        command = MetaCommand.query(identifier=identifier)
        self.__broadcast_command(content=command, receiver=Station.EVERY)
        return True

    # Override
    def query_document(self, identifier: ID) -> bool:
        checker = QueryFrequencyChecker()
        if not checker.document_query_expired(identifier=identifier):
            # query not expired yet
            self.debug(msg='document query not expired yet: %s' % identifier)
            return False
        self.info(msg='querying document of %s from neighbor stations' % identifier)
        command = DocumentCommand.query(identifier=identifier)
        self.__broadcast_command(content=command, receiver=Station.EVERY)
        return True

    # Override
    def query_members(self, identifier: ID) -> bool:
        # station will never process group info
        return True

    # protected
    # noinspection PyMethodMayBeStatic
    def is_blocked(self, msg: ReliableMessage) -> bool:
        block_filter = FilterManager().block_filter
        return block_filter.is_blocked(msg=msg)

    # Override
    def verify_message(self, msg: ReliableMessage) -> Optional[SecureMessage]:
        # check block list
        if self.is_blocked(msg=msg):
            self.warning(msg='user is blocked: %s -> %s (group: %s)' % (msg.sender, msg.receiver, msg.group))
            return None
        sender = msg.sender
        receiver = msg.receiver
        current = self.facebook.current_user
        sid = current.identifier
        # 1. verify message
        s_msg = super().verify_message(msg=msg)
        if receiver == sid:
            # message to this station
            # maybe a meta command, document command, etc ...
            return s_msg
        elif receiver.is_broadcast:
            # if receiver == 'station@anywhere':
            #     it must be the first handshake without station ID;
            # if receiver == 'anyone@anywhere':
            #     it should be other plain message without encryption.
            # if receiver.is_group:
            #     broadcast message to multiple destinations,
            #     current station is it's receiver too.
            if receiver.is_group:
                # broadcast to neighbor stations
                self.__broadcast_reliable_message(msg=msg, station=sid)
            elif receiver == 'archivist@anywhere':
                # forward to search bot
                self.__broadcast_reliable_message(msg=msg, station=sid)
                return None
            return s_msg
        elif receiver.is_group:
            self.error(msg='group message should not send to station: %s -> %s' % (sender, receiver))
            return None

        # 2. check session for delivering
        session = self.session
        if session.identifier is None or not session.active:
            # not login? ask client to handshake again (with session key)
            # this message won't be delivered before handshake accepted
            cmd = HandshakeCommand.ask(session=session.key)
            self.send_content(sender=sid, receiver=sender, content=cmd)
            # DISCUSS: suspend this message for waiting handshake accepted
            #          or let the client to send it again?
            return None
        # session is active, so this message is not for current station,
        # deliver to the real receiver and respond to sender
        dispatcher = Dispatcher()
        dispatcher.deliver_message(msg=msg, receiver=receiver)
        # TODO: send responses to the sender?

    # Override
    def process_reliable_message(self, msg: ReliableMessage) -> List[ReliableMessage]:
        # call super
        responses = super().process_reliable_message(msg=msg)
        current = self.facebook.current_user
        sid = current.identifier
        # check for first login
        if msg.receiver == Station.ANY or msg.group == Station.EVERY:
            # if this message sent to 'station@anywhere', or with group ID 'stations@everywhere',
            # it means the client doesn't have the station's meta (e.g.: first handshaking)
            # or visa maybe expired, here attach them to the first response.
            for res in responses:
                if res.sender == sid:
                    # let the first responding message to carry the station's meta & visa
                    res.meta = current.meta
                    res.visa = current.visa
                    break
        else:
            session = self.session
            if session.identifier == sid:
                # station bridge
                responses = pick_out(messages=responses, bridge=sid)
        return responses


def pick_out(messages: List[ReliableMessage], bridge: ID) -> List[ReliableMessage]:
    responses = []
    dispatcher = Dispatcher()
    for msg in messages:
        receiver = msg.receiver
        if receiver == bridge:
            # respond to the bridge
            responses.append(msg)
        else:
            # this message is not respond to the bridge, the receiver may be
            # roaming to other station, so deliver it via dispatcher here.
            dispatcher.deliver_message(msg=msg, receiver=receiver)
    return responses


def get_neighbors(db: SessionDBI) -> Set[ID]:
    neighbors = set()
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
    proactive_neighbors = NeighborSessionManager().proactive_neighbors
    for sid in proactive_neighbors:
        if sid is None or sid.is_broadcast:
            assert False, 'neighbor station ID error: %s' % sid
            # continue
        neighbors.add(sid)
    return neighbors


@Singleton
class NeighborSessionManager:

    def __init__(self):
        super().__init__()
        self.__neighbors = set()
        self.__expires = 0
        self.__lock = threading.Lock()

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


def get_recipients(msg: ReliableMessage, receiver: ID, db: SessionDBI) -> Set[ID]:
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
        neighbors = get_neighbors(db=db)
        for sid in neighbors:
            if sid not in traces:  # and sid != station:
                recipients.add(sid)
            else:
                Log.warning(msg='ignore neighbor: %s' % sid)
        # get archivist bot
        if receiver == EVERYONE:
            # include 'archivist' as 'everyone@everywhere'
            bot = ans_id(name='archivist')
            if bot is not None and bot not in traces:
                recipients.add(bot)
    elif receiver == 'archivist@anywhere' or receiver == 'archivists@everywhere':
        Log.info(msg='forward to archivist: %s' % receiver)
        # get archivist bot for search command
        bot = ans_id(name='archivist')
        if bot is not None and bot not in traces:
            recipients.add(bot)
    Log.info(msg='recipients: %s -> %s' % (receiver, recipients))
    return recipients


def ans_id(name: str) -> Optional[ID]:
    try:
        return ID.parse(identifier=name)
    except ValueError as e:
        Log.warning(msg='ANS record not exists: %s, %s' % (name, e))
