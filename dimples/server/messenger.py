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

from typing import Optional, List

from dimsdk import ID, ANYONE
from dimsdk import Station
from dimsdk import Envelope, Command, MetaCommand, DocumentCommand
from dimsdk import InstantMessage
from dimsdk import SecureMessage, ReliableMessage

from ..utils import QueryFrequencyChecker
from ..common import HandshakeCommand
from ..common import CommonMessenger

from .packer import FilterManager
from .dispatcher import Dispatcher
from .broadcast import broadcast_reliable_message


class ServerMessenger(CommonMessenger):

    # Override
    def handshake_success(self):
        session = self.session
        identifier = session.identifier
        remote_address = session.remote_address
        self.warning(msg='user login: %s, socket: %s' % (identifier, remote_address))
        # process suspended messages
        messages = self._resume_reliable_messages()
        for msg in messages:
            self.info(msg='processing suspended message: %s -> %s' % (msg.sender, msg.receiver))
            try:
                responses = self.process_reliable_message(msg=msg)
                for res in responses:
                    self.send_reliable_message(msg=res, priority=1)
            except Exception as error:
                self.error(msg='failed to process incoming message: %s' % error)

    def _broadcast_command(self, content: Command, receiver: ID):
        sid = self.facebook.current_user.identifier
        env = Envelope.create(sender=sid, receiver=receiver)
        i_msg = InstantMessage.create(head=env, body=content)
        # pack & deliver message
        s_msg = self.encrypt_message(msg=i_msg)
        r_msg = self.sign_message(msg=s_msg)
        broadcast_reliable_message(msg=r_msg, station=sid)

    # Override
    def query_meta(self, identifier: ID) -> bool:
        checker = QueryFrequencyChecker()
        if not checker.meta_query_expired(identifier=identifier):
            # query not expired yet
            self.debug(msg='meta query not expired yet: %s' % identifier)
            return False
        self.info(msg='querying meta of %s from neighbor stations' % identifier)
        command = MetaCommand.query(identifier=identifier)
        self._broadcast_command(content=command, receiver=Station.EVERY)
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
        self._broadcast_command(content=command, receiver=Station.EVERY)
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
        # 1. check receiver
        if receiver != sid and receiver != Station.ANY:  # and receiver != Station.EVERY:
            # message not for this station, check session for delivering
            session = self.session
            if session.identifier is None or not session.active:
                # not login?
                # 1.1. suspend this message for waiting handshake
                error = {
                    'message': 'user not login',
                }
                self.suspend_reliable_message(msg=msg, error=error)
                # 1.2. ask client to handshake again (with session key)
                # this message won't be delivered before handshake accepted
                cmd = HandshakeCommand.ask(session=session.key)
                self.send_content(sender=sid, receiver=sender, content=cmd)
                return None
            # session is active and user login success
            # if sender == session.ID,
            #   we can trust this message an no need to verify it;
            # else if sender is a neighbor station,
            #   we can trust it too;
        # 2. verify message
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
            if receiver == Station.ANY or receiver == ANYONE:
                return s_msg
            # broadcast message (to neighbor stations, or station bots)
            broadcast_reliable_message(msg=msg, station=sid)
            # if receiver.is_group:
            #     broadcast message to multiple destinations,
            #     current station is it's receiver too.
            if receiver.is_group:
                return s_msg
            # otherwise, this message should have been redirected
            # e.g.: 'archivist@anywhere', 'apns@anywhere'
            return None
        elif receiver.is_group:
            self.error(msg='group message should not send to station: %s -> %s' % (sender, receiver))
            return None
        # 3. this message is not for current station,
        # deliver to the real receiver and respond to sender
        dispatcher = Dispatcher()
        responses = dispatcher.deliver_message(msg=msg, receiver=receiver)
        assert len(responses) > 0, 'should not happen'
        for res in responses:
            self.send_content(sender=sid, receiver=sender, content=res)

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
