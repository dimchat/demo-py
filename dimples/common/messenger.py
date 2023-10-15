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

import threading
from abc import ABC, abstractmethod
from typing import Optional, Tuple, List, Dict

from dimsdk import SymmetricKey
from dimsdk import ID
from dimsdk import Content, Envelope
from dimsdk import Command
from dimsdk import InstantMessage, SecureMessage, ReliableMessage
from dimsdk import EntityDelegate, CipherKeyDelegate
from dimsdk import Messenger, Packer, Processor

from ..utils import Logging

from .dbi import MessageDBI

from .facebook import CommonFacebook
from .session import Transmitter, Session

from .compat import fix_command


class CommonMessenger(Messenger, Transmitter, Logging, ABC):

    def __init__(self, session: Session, facebook: CommonFacebook, database: MessageDBI):
        super().__init__()
        self.__session = session
        self.__facebook = facebook
        self.__database = database
        self.__packer: Optional[Packer] = None
        self.__processor: Optional[Processor] = None
        # suspended messages
        self.__suspend_lock = threading.Lock()
        self.__incoming_messages: List[ReliableMessage] = []
        self.__outgoing_messages: List[InstantMessage] = []

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

    @abstractmethod
    def handshake_success(self):
        """ callback for handshake success """
        raise NotImplemented

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

    #
    #   Suspend messages
    #

    def suspend_reliable_message(self, msg: ReliableMessage, error: Dict):
        """
        Add income message in a queue for waiting sender's visa

        :param msg:   incoming message
        :param error: error info
        """
        self.warning(msg='suspend message: %s -> %s, %s' % (msg.sender, msg.receiver, error))
        msg['error'] = error
        with self.__suspend_lock:
            if len(self.__incoming_messages) > 32:
                self.__incoming_messages.pop(0)
            self.__incoming_messages.append(msg)

    def _resume_reliable_messages(self) -> List[ReliableMessage]:
        with self.__suspend_lock:
            messages = self.__incoming_messages
            self.__incoming_messages = []
            return messages

    def suspend_instant_message(self, msg: InstantMessage, error: Dict):
        """
        Add outgo message in a queue for waiting receiver's visa

        :param msg:   outgo message
        :param error: error info
        """
        self.warning(msg='suspend message: %s -> %s, %s' % (msg.sender, msg.receiver, error))
        msg['error'] = error
        with self.__suspend_lock:
            if len(self.__outgoing_messages) > 32:
                self.__outgoing_messages.pop(0)
            self.__outgoing_messages.append(msg)

    def _resume_instant_messages(self) -> List[InstantMessage]:
        with self.__suspend_lock:
            messages = self.__outgoing_messages
            self.__outgoing_messages = []
            return messages

    # Override
    def serialize_content(self, content: Content, key: SymmetricKey, msg: InstantMessage) -> bytes:
        if isinstance(content, Command):
            content = fix_command(content=content)
        return super().serialize_content(content=content, key=key, msg=msg)

    # Override
    def deserialize_content(self, data: bytes, key: SymmetricKey, msg: SecureMessage) -> Optional[Content]:
        content = super().deserialize_content(data=data, key=key, msg=msg)
        if isinstance(content, Command):
            content = fix_command(content=content)
        return content

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
