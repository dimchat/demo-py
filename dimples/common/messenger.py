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
from typing import Optional, Tuple

from dimsdk import ID
from dimsdk import InstantMessage, SecureMessage, ReliableMessage
from dimsdk import Content, Envelope
from dimsdk import GroupCommand
from dimsdk import EntityDelegate, CipherKeyDelegate
from dimsdk import Messenger, Packer, Processor

from ..utils import Logging

from .dbi import MessageDBI

from .checker import QueryFrequencyChecker
from .facebook import CommonFacebook
from .transmitter import Transmitter
from .session import Session


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

    @abstractmethod
    def _query_document(self, identifier: ID) -> bool:
        """ request for meta & visa document with entity ID """
        raise NotImplemented

    def _query_members(self, identifier: ID) -> bool:
        """ request for group members with group ID """
        checker = QueryFrequencyChecker()
        if not checker.members_query_expired(identifier=identifier):
            # query not expired yet
            self.debug(msg='members query not expired yet: %s' % identifier)
            return False
        assert identifier.is_group, 'group ID error: %s' % identifier
        group = self.facebook.group(identifier=identifier)
        # request to group bots
        assistants = group.assistants
        if assistants is None or len(assistants) == 0:
            self.error(msg='group assistants not found: %s' % identifier)
            return False
        self.info(msg='querying members of %s from assistants: %s' % (identifier, ID.revert(members=assistants)))
        cmd = GroupCommand.query(group=identifier)
        for bot in assistants:
            self.send_content(sender=None, receiver=bot, content=cmd)
        return True

    def _check_sender(self, msg: ReliableMessage) -> bool:
        """ check whether msg.sender is ready """
        sender = msg.sender
        assert sender.is_user, 'sender error: %s' % sender
        # check sender's meta & document
        visa = msg.visa
        if visa is not None:
            # first handshake?
            assert visa.identifier == sender, 'visa ID not match: %s => %s' % (sender, visa)
            # assert Meta.matches(meta=msg.meta, identifier=sender), 'meta error: %s' % msg
            return True
        facebook = self.facebook
        verify_keys = facebook.public_keys_for_verification(identifier=sender)
        if verify_keys is not None and len(verify_keys) > 0:
            # sender is OK
            return True
        self._query_document(identifier=sender)
        msg['error'] = {
            'message': 'verify key not found',
            'user': str(sender),
        }

    def _check_receiver(self, msg: InstantMessage) -> bool:
        """ check whether msg.receiver is ready """
        receiver = msg.receiver
        facebook = self.facebook
        if receiver.is_user:
            # check user's meta & document
            visa_key = facebook.public_key_for_encryption(identifier=receiver)
            if visa_key is None:
                self._query_document(identifier=receiver)
                msg['error'] = {
                    'message': 'encrypt key not found',
                    'user': str(receiver),
                }
                return False
        else:
            # check group's meta
            meta = facebook.meta(identifier=receiver)
            if meta is None:
                self._query_document(identifier=receiver)
                msg['error'] = {
                    'message': 'group meta not found',
                    'group': str(receiver),
                }
                return False
            # check group members
            members = facebook.members(identifier=receiver)
            if members is None or len(members) == 0:
                self._query_members(identifier=receiver)
                msg['error'] = {
                    'message': 'members not found',
                    'group': str(receiver),
                }
                return False
            waiting = set()
            for item in members:
                user = facebook.user(identifier=item)
                if user is None:
                    waiting.add(user)
            if len(waiting) > 0:
                msg['error'] = {
                    'message': 'encrypt keys not found',
                    'group': str(receiver),
                    'members': ID.revert(members=waiting)
                }
                return False
        # receiver is OK
        return True

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
    def encrypt_message(self, msg: InstantMessage) -> Optional[SecureMessage]:
        if self._check_receiver(msg=msg):
            return super().encrypt_message(msg=msg)
        else:
            self.warning(msg='receiver not ready: %s' % msg.receiver)

    # Override
    def verify_message(self, msg: ReliableMessage) -> Optional[SecureMessage]:
        if self._check_sender(msg=msg):
            return super().verify_message(msg=msg)
        else:
            self.warning(msg='sender not ready: %s' % msg.sender)

    #
    #   Interfaces for Transmitting Message
    #

    # Override
    def send_content(self, sender: Optional[ID], receiver: ID, content: Content,
                     priority: int = 0) -> Tuple[InstantMessage, Optional[ReliableMessage]]:
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
        # 1. serialize message
        data = self.serialize_message(msg=msg)
        assert data is not None, 'failed to serialize message: %s' % msg
        # 2. call gate keeper to send the message data package
        #    put message package into the waiting queue of current session
        session = self.session
        return session.queue_message_package(msg=msg, data=data, priority=priority)
