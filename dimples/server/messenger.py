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

from dimsdk import EntityType
from dimsdk import Station
from dimsdk import SecureMessage, ReliableMessage
from dimsdk import Processor

from ..common import HandshakeCommand
from ..common import MessageDBI
from ..common import CommonMessenger, CommonFacebook
from ..common import Session

from .filter import Filter, DefaultFilter
from .dispatcher import Dispatcher


class ServerMessenger(CommonMessenger):

    def __init__(self, session: Session, facebook: CommonFacebook, database: MessageDBI):
        super().__init__(session=session, facebook=facebook, database=database)
        # NOTICE: create Filter by RequestHandler
        self.__filter = DefaultFilter(session=session, facebook=facebook)

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
        # 3. check session for delivering
        session = self.session
        if session.identifier is None or not session.active:
            # not login
            if receiver.is_broadcast:
                # first handshake without station ID?
                # return it for processing
                return s_msg
            # ask client to handshake (with session key) again
            cmd = HandshakeCommand.ask(session=session.key)
            self.send_content(sender=current.identifier, receiver=sender, content=cmd)
            return None
        # 4. deliver message
        #    broadcast message should deliver to other stations;
        #    group message should deliver to group assistants.
        dispatcher = Dispatcher()
        if receiver.is_broadcast:
            # call dispatcher to broadcast to neighbour station(s);
            # current station is also a broadcast message's target,
            # so return it to let this station process it.
            dispatcher.deliver_message(msg=msg)
            return s_msg
        else:
            # this message is not for this station,
            # store and deliver to the real destination.
            db = self.database
            db.save_reliable_message(msg=msg)
            dispatcher.deliver_message(msg=msg)
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
            user = self.facebook.current_user
            for res in responses:
                if res.sender == user.identifier:
                    # let the first responding message to carry the station's meta & visa
                    res.meta = user.meta
                    res.visa = user.visa
                    break
        return responses
