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

from typing import Optional, List, Dict

from dimsdk import EntityType, ID, ANYONE
from dimsdk import Station
from dimsdk import Envelope, MetaCommand, DocumentCommand
from dimsdk import InstantMessage
from dimsdk import SecureMessage, ReliableMessage

from ..utils import QueryFrequencyChecker
from ..common import HandshakeCommand
from ..common import MessageDBI
from ..common import CommonMessenger, CommonFacebook
from ..common import Session

from .filter import Filter
from .dispatcher import Dispatcher


class ServerMessenger(CommonMessenger):

    def __init__(self, session: Session, facebook: CommonFacebook, database: MessageDBI):
        super().__init__(session=session, facebook=facebook, database=database)
        # NOTICE: create Filter by RequestHandler
        self.__filter: Optional[Filter] = None

    @property
    def filter(self) -> Filter:
        return self.__filter

    @filter.setter
    def filter(self, checker: Filter):
        self.__filter = checker

    # Override
    def query_meta(self, identifier: ID) -> bool:
        checker = QueryFrequencyChecker()
        if not checker.meta_query_expired(identifier=identifier):
            # query not expired yet
            self.debug(msg='meta query not expired yet: %s' % identifier)
            return False
        self.info(msg='querying meta of %s from neighbor stations' % identifier)
        current = self.facebook.current_user
        stations = Station.EVERY
        cmd = MetaCommand.query(identifier=identifier)
        env = Envelope.create(sender=current.identifier, receiver=stations)
        i_msg = InstantMessage.create(head=env, body=cmd)
        # pack & deliver message
        s_msg = self.encrypt_message(msg=i_msg)
        r_msg = self.sign_message(msg=s_msg)
        dispatcher = Dispatcher()
        dispatcher.deliver_message(msg=r_msg, receiver=stations)
        return True

    # Override
    def query_document(self, identifier: ID) -> bool:
        checker = QueryFrequencyChecker()
        if not checker.document_query_expired(identifier=identifier):
            # query not expired yet
            self.debug(msg='document query not expired yet: %s' % identifier)
            return False
        self.info(msg='querying document of %s from neighbor stations' % identifier)
        current = self.facebook.current_user
        stations = Station.EVERY
        cmd = DocumentCommand.query(identifier=identifier)
        env = Envelope.create(sender=current.identifier, receiver=stations)
        i_msg = InstantMessage.create(head=env, body=cmd)
        # pack & deliver message
        s_msg = self.encrypt_message(msg=i_msg)
        r_msg = self.sign_message(msg=s_msg)
        dispatcher = Dispatcher()
        dispatcher.deliver_message(msg=r_msg, receiver=stations)
        return True

    # Override
    def query_members(self, identifier: ID) -> bool:
        # station will never process group info
        return True

    # Override
    def suspend_reliable_message(self, msg: ReliableMessage, error: Dict):
        # TODO: suspend message for waiting msg.sender's meta/visa
        pass

    # Override
    def suspend_instant_message(self, msg: InstantMessage, error: Dict):
        # TODO: suspend message for waiting msg.receiver's visa
        pass

    # Override
    def verify_message(self, msg: ReliableMessage) -> Optional[SecureMessage]:
        sender = msg.sender
        receiver = msg.receiver
        checker = self.filter
        # 0. check msg['traces']
        if checker.check_traced(msg=msg):
            # cycled message
            if sender.type == EntityType.STATION or receiver.type == EntityType.STATION:
                # ignore cycled station message
                return None
            elif receiver.is_broadcast:
                # ignore cycled broadcast message
                return None
        # 1. verify message
        if checker.trusted_sender(sender=sender):
            # no need to verify message from this sender
            s_msg = msg
        else:
            s_msg = super().verify_message(msg=msg)
            if s_msg is None:
                # failed to verify message
                return None
        # 2. check message for current station
        facebook = self.facebook
        current = facebook.current_user
        if receiver == current.identifier:
            # message to this station
            return s_msg
        elif receiver.is_broadcast and receiver.is_user:
            # broadcast message to single destination
            if receiver == Station.ANY:
                # message to 'station@anywhere'
                # for first handshake without station ID
                return s_msg
            elif receiver == ANYONE:
                # message to 'anyone@anywhere'
                # other plain message without encryption?
                return s_msg
        # 3. check session for delivering
        session = self.session
        if session.identifier is None or not session.active:
            # not login? ask client to handshake again (with session key)
            # this message won't be delivered before handshake accepted
            cmd = HandshakeCommand.ask(session=session.key)
            self.send_content(sender=current.identifier, receiver=sender, content=cmd)
            # DISCUSS: suspend this message for waiting handshake accepted
            #          or let the client to send it again?
            return None
        # 4. deliver message and respond to sender
        #    broadcast message should deliver to other stations;
        #    group message should deliver to group assistant(s).
        dispatcher = Dispatcher()
        responses = dispatcher.deliver_message(msg=msg, receiver=receiver)
        for res in responses:
            self.send_content(sender=current.identifier, receiver=sender, content=res)
        # 5. OK
        if receiver.is_broadcast and receiver.is_group:
            # broadcast message to multiple destinations,
            # current station is it's receiver too,
            # so return it to let this station process it.
            return s_msg
        else:
            # this message is not for this station,
            # let dispatcher deliver to the real receiver.
            return None

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
