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

from dimsdk import EntityType, ANYONE
from dimsdk import Station
from dimsdk import SecureMessage, ReliableMessage
from dimsdk import Processor

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
    def _create_processor(self) -> Processor:
        from .processor import ServerProcessor
        return ServerProcessor(facebook=self.facebook, messenger=self)

    # Override
    def send_message_package(self, msg: ReliableMessage, data: bytes, priority: int = 0) -> bool:
        """ put message package into the waiting queue of current session """
        session = self.session
        return session.queue_message_package(msg=msg, data=data, priority=priority)

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
        responses = dispatcher.deliver_message(msg=msg)
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
        receiver = msg.receiver
        group = msg.group
        # check for first login
        if receiver == Station.ANY or (group is not None and group.is_broadcast):
            # if this message sent to 'station@anywhere', or with group ID 'stations@everywhere',
            # it means the client doesn't have the station's meta or visa (e.g.: first handshaking),
            # so respond them as message attachments.
            current = self.facebook.current_user
            uid = current.identifier
            for res in responses:
                if res.sender == uid:
                    # let the first responding message to carry the station's meta & visa
                    res.meta = current.meta
                    res.visa = current.visa
                    break
        return responses
