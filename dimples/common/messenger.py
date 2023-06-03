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
from typing import Optional, Tuple, List, Dict

from dimsdk import EncryptKey, ID
from dimsdk import InstantMessage, SecureMessage, ReliableMessage
from dimsdk import Content, Envelope
from dimsdk import EntityDelegate, CipherKeyDelegate
from dimsdk import Messenger, Packer, Processor

from ..utils import Logging

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

    @abstractmethod  # protected
    def suspend_reliable_message(self, msg: ReliableMessage, error: Dict):
        """ Add income message in a queue for waiting sender's visa """
        raise NotImplemented

    @abstractmethod  # protected
    def suspend_instant_message(self, msg: InstantMessage, error: Dict):
        """ Add outgo message in a queue for waiting receiver's visa """
        raise NotImplemented

    def _visa_key(self, user: ID) -> Optional[EncryptKey]:
        """ for checking whether user's ready """
        key = self.facebook.public_key_for_encryption(identifier=user)
        if key is not None:
            # user is ready
            return key
        # user not ready, try to query document for it
        if self.query_document(identifier=user):
            self.info(msg='querying document for user: %s' % user)

    def _members(self, group: ID) -> List[ID]:
        """ for checking whether group's ready """
        meta = self.facebook.meta(identifier=group)
        if meta is None:
            # group not ready, try to query meta for it
            if self.query_meta(identifier=group):
                self.info(msg='querying meta for group: %s' % group)
            return []
        grp = self.facebook.group(identifier=group)
        members = grp.members
        if members is None or len(members) == 0:
            # group not ready, try to query members for it
            if self.query_members(identifier=group):
                self.info(msg='querying members for group: %s' % group)
            return []
        # group is ready
        return members

    def _check_reliable_message_sender(self, msg: ReliableMessage) -> bool:
        """ Check sender before verifying received message """
        sender = msg.sender
        assert sender.is_user, 'sender error: %s' % sender
        # check sender's meta & document
        visa = msg.visa
        if visa is not None:
            # first handshake?
            assert visa.identifier == sender, 'visa ID not match: %s => %s' % (sender, visa)
            # assert Meta.match_id(meta=msg.meta, identifier=sender), 'meta error: %s' % msg
            return True
        elif self._visa_key(user=sender) is not None:
            # sender is OK
            return True
        # sender not ready, suspend message for waiting document
        error = {
            'message': 'verify key not found',
            'user': str(sender),
        }
        self.suspend_reliable_message(msg=msg, error=error)  # msg['error'] = error

    def _check_secure_message_receiver(self, msg: SecureMessage) -> bool:
        receiver = msg.receiver
        if receiver.is_broadcast:
            # broadcast message
            return True
        elif receiver.is_group:
            # check for received group message
            members = self._members(group=receiver)
            return len(members) > 0
        # the facebook will select a user from local users to match this receiver,
        # if no user matched (private key not found), this message will be ignored.
        return True

    def _check_instant_message_receiver(self, msg: InstantMessage) -> bool:
        """ Check receiver before encrypting message """
        receiver = msg.receiver
        if receiver.is_broadcast:
            # broadcast message
            return True
        elif receiver.is_group:
            # NOTICE: station will never send group message, so
            #         we don't need to check group info here; and
            #         if a client wants to send group message,
            #         that should be sent to a group bot first,
            #         and the bot will separate it for all members.
            return False
        elif self._visa_key(user=receiver) is not None:
            # receiver is OK
            return True
        # receiver not ready, suspend message for waiting document
        error = {
            'message': 'encrypt key not found',
            'user': str(receiver),
        }
        self.suspend_instant_message(msg=msg, error=error)  # msg['error'] = error

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
        if self._check_instant_message_receiver(msg=msg):
            # receiver OK
            pass
        else:
            # receiver not ready
            error = 'receiver not ready: %s' % msg.receiver
            self.warning(msg=error)
            raise LookupError(error)
        return super().encrypt_message(msg=msg)

    # Override
    def verify_message(self, msg: ReliableMessage) -> Optional[SecureMessage]:
        if self._check_secure_message_receiver(msg=msg):
            # receiver OK
            pass
        else:
            # receiver (group) not ready
            self.warning(msg='receiver not ready: %s' % msg.receiver)
            return None
        if self._check_reliable_message_sender(msg=msg):
            # sender OK
            pass
        else:
            # sender not ready
            self.warning(msg='sender not ready: %s' % msg.sender)
            return None
        return super().verify_message(msg=msg)

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
