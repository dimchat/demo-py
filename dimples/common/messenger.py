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
from typing import Optional

from dimsdk import ID
from dimsdk import InstantMessage, ReliableMessage
from dimsdk import Content, Envelope
from dimsdk import EntityDelegate, CipherKeyDelegate
from dimsdk import Messenger, Packer, Processor

from .dbi import MessageDBI

from .facebook import CommonFacebook
from .transmitter import Transmitter
from .session import Session


class CommonMessenger(Messenger, Transmitter, ABC):

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

    #
    #   Interfaces for Transmitting Message
    #

    # Override
    def send_content(self, sender: Optional[ID], receiver: ID, content: Content,
                     priority: int = 0) -> (InstantMessage, Optional[ReliableMessage]):
        """ Send message content with priority """
        # Application Layer should make sure user is already login before it send message to server.
        # Application layer should put message into queue so that it will send automatically after user login
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

    # Override
    def send_reliable_message(self, msg: ReliableMessage, priority: int = 0) -> bool:
        """ send reliable message with priority """
        data = self.serialize_message(msg=msg)
        assert data is not None, 'failed to serialize message: %s' % msg
        return self.send_message_package(msg=msg, data=data, priority=priority)

    @abstractmethod
    def send_message_package(self, msg: ReliableMessage, data: bytes, priority: int = 0) -> bool:
        """ call gate keeper to send the message data package """
        raise NotImplemented
