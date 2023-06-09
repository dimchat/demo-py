# -*- coding: utf-8 -*-
# ==============================================================================
# MIT License
#
# Copyright (c) 2022 Albert Moky
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
    Common extensions for Messenger
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    Transform and send message
"""

from abc import ABC, abstractmethod
from typing import Optional, Tuple, List

from dimsdk import EntityType, ID
from dimsdk import ContentType, Content, Envelope
from dimsdk import InstantMessage, ReliableMessage
from dimsdk import EntityDelegate, CipherKeyDelegate
from dimsdk import Messenger, Packer, Processor

from ..utils import Logging
from ..common import ReceiptCommand

from .dbi import MessageDBI

from .facebook import CommonFacebook
from .session import Transmitter, Session


class CommonMessenger(Messenger, Transmitter, Logging, ABC):

    def __init__(self, session: Session, facebook: CommonFacebook, database: MessageDBI):
        super().__init__()
        self.__session = session
        self.__facebook = facebook
        self.__database = database
        self.__packer: Optional[Packer] = None
        self.__processor: Optional[Processor] = None

    @property  # Override
    def packer(self) -> Packer:
        return self.__packer

    @packer.setter
    def packer(self, delegate: Packer):
        self.__packer = delegate

    @property  # Override
    def processor(self) -> Processor:
        return self.__processor

    @processor.setter
    def processor(self, delegate: Processor):
        self.__processor = delegate

    @property
    def database(self) -> MessageDBI:
        return self.__database

    @property  # Override
    def key_cache(self) -> CipherKeyDelegate:
        return self.__database

    @property  # Override
    def barrack(self) -> EntityDelegate:
        return self.__facebook

    @property
    def facebook(self) -> CommonFacebook:
        return self.__facebook

    @property
    def session(self) -> Session:
        return self.__session

    @abstractmethod  # protected
    def query_meta(self, identifier: ID) -> bool:
        """ request for meta with entity ID """
        raise NotImplemented

    @abstractmethod  # protected
    def query_document(self, identifier: ID) -> bool:
        """ request for meta & visa document with entity ID """
        raise NotImplemented

    @abstractmethod  # protected
    def query_members(self, identifier: ID) -> bool:
        """ request for group members with group ID """
        raise NotImplemented

    # # Override
    # def serialize_key(self, key: Union[dict, SymmetricKey], msg: InstantMessage) -> Optional[bytes]:
    #     # try to reuse message key
    #     reused = key.get('reused')
    #     if reused is not None:
    #         if msg.receiver.is_group:
    #             # reuse key for grouped message
    #             return None
    #         # remove before serialize key
    #         key.pop('reused', None)
    #     data = super().serialize_key(key=key, msg=msg)
    #     if reused is not None:
    #         # put it back
    #         key['reused'] = reused
    #     return data

    # Override
    def process_reliable_message(self, msg: ReliableMessage) -> List[ReliableMessage]:
        # call super
        responses = super().process_reliable_message(msg=msg)
        if len(responses) == 0 and self._needs_receipt(msg=msg):
            current_user = self.facebook.current_user
            res = ReceiptCommand.create(text='Message received', msg=msg)
            env = Envelope.create(sender=current_user.identifier, receiver=msg.sender)
            i_msg = InstantMessage.create(head=env, body=res)
            s_msg = self.encrypt_message(msg=i_msg)
            assert s_msg is not None, 'failed to encrypt message: %s -> %s' % (current_user, msg.sender)
            r_msg = self.sign_message(msg=s_msg)
            assert r_msg is not None, 'failed to sign message: %s -> %s' % (current_user, msg.sender)
            responses = [r_msg]
        return responses

    # noinspection PyMethodMayBeStatic
    def _needs_receipt(self, msg: ReliableMessage) -> bool:
        if msg.type == ContentType.COMMAND:
            # filter for looping message (receipt for receipt)
            return False
        sender = msg.sender
        receiver = msg.receiver
        if sender.type == EntityType.STATION or sender.type == EntityType.BOT:
            if receiver.type == EntityType.STATION or receiver.type == EntityType.BOT:
                # message between bots
                return False
        # current_user = self.facebook.current_user
        # if receiver != current_user.identifier:
        #     # forward message
        #     return True
        # TODO: other condition?
        return True

    #
    #   Interfaces for Transmitting Message
    #

    # Override
    def send_content(self, sender: Optional[ID], receiver: ID, content: Content,
                     priority: int = 0) -> Tuple[InstantMessage, Optional[ReliableMessage]]:
        """ Send message content with priority """
        if sender is None:
            current = self.facebook.current_user
            assert current is not None, 'current user not set'
            sender = current.identifier
        env = Envelope.create(sender=sender, receiver=receiver)
        i_msg = InstantMessage.create(head=env, body=content)
        r_msg = self.send_instant_message(msg=i_msg, priority=priority)
        return i_msg, r_msg

    # Override
    def send_instant_message(self, msg: InstantMessage, priority: int = 0) -> Optional[ReliableMessage]:
        """ send instant message with priority """
        # send message (secured + certified) to target station
        s_msg = self.encrypt_message(msg=msg)
        if s_msg is None:
            # public key not found?
            return None
        r_msg = self.sign_message(msg=s_msg)
        if r_msg is None:
            # TODO: set msg.state = error
            raise AssertionError('failed to sign message: %s' % s_msg)
        if self.send_reliable_message(msg=r_msg, priority=priority):
            return r_msg
        # failed

    # Override
    def send_reliable_message(self, msg: ReliableMessage, priority: int = 0) -> bool:
        """ send reliable message with priority """
        # 1. serialize message
        data = self.serialize_message(msg=msg)
        assert data is not None, 'failed to serialize message: %s' % msg
        # 2. call gate keeper to send the message data package
        #    put message package into the waiting queue of current session
        session = self.session
        return session.queue_message_package(msg=msg, data=data, priority=priority)
