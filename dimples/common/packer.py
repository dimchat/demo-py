# -*- coding: utf-8 -*-
# ==============================================================================
# MIT License
#
# Copyright (c) 2023 Albert Moky
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

from abc import ABC
from typing import Optional, Dict, List

from dimsdk import EncryptKey
from dimsdk import ID
from dimsdk import InstantMessage, SecureMessage, ReliableMessage
from dimsdk import MessagePacker

from ..utils import Logging


class CommonMessagePacker(MessagePacker, Logging, ABC):

    # protected
    def _suspend_reliable_message(self, msg: ReliableMessage, error: Dict):
        """ Add income message in a queue for waiting sender's visa """
        pass

    # protected
    def _suspend_instant_message(self, msg: InstantMessage, error: Dict):
        """ Add outgo message in a queue for waiting receiver's visa """
        pass

    # protected
    def _visa_key(self, user: ID) -> Optional[EncryptKey]:
        """ for checking whether user's ready """
        facebook = get_facebook(packer=self)
        key = facebook.public_key_for_encryption(identifier=user)
        if key is not None:
            # user is ready
            return key
        # user not ready, try to query document for it
        messenger = get_messenger(packer=self)
        if messenger.query_document(identifier=user):
            self.info(msg='querying document for user: %s' % user)

    # protected
    def _members(self, group: ID) -> Optional[List[ID]]:
        """ for checking whether group's ready """
        facebook = get_facebook(packer=self)
        messenger = get_messenger(packer=self)
        meta = facebook.meta(identifier=group)
        if meta is None:  # or meta.key is None:
            # group not ready, try to query meta for it
            if messenger.query_meta(identifier=group):
                self.info(msg='querying meta for group: %s' % group)
            return None
        grp = facebook.group(identifier=group)
        members = grp.members
        if members is None or len(members) == 0:
            # group not ready, try to query members for it
            if messenger.query_members(identifier=group):
                self.info(msg='querying members for group: %s' % group)
            return None
        # group is ready
        return members

    # protected
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
        self._suspend_reliable_message(msg=msg, error=error)  # msg['error'] = error
        return False

    # protected
    def _check_reliable_message_receiver(self, msg: ReliableMessage) -> bool:
        receiver = msg.receiver
        if receiver.is_broadcast:
            # broadcast message
            return True
        elif receiver.is_user:
            # the facebook will select a user from local users to match this receiver,
            # if no user matched (private key not found), this message will be ignored.
            return True
        # check for received group message
        members = self._members(group=receiver)
        if members is not None:
            return True
        # group not ready, suspend message for waiting members
        error = {
            'message': 'group not ready',
            'group': str(receiver),
        }
        self._suspend_reliable_message(msg=msg, error=error)  # msg['error'] = error
        return False

    # protected
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
        self._suspend_instant_message(msg=msg, error=error)  # msg['error'] = error
        return False

    # Override
    def encrypt_message(self, msg: InstantMessage) -> Optional[SecureMessage]:
        if not self._check_instant_message_receiver(msg=msg):
            # receiver not ready
            self.warning(msg='receiver not ready: %s' % msg.receiver)
            return None
        return super().encrypt_message(msg=msg)

    # Override
    def sign_message(self, msg: SecureMessage) -> ReliableMessage:
        if isinstance(msg, ReliableMessage):
            # already signed
            return msg
        return super().sign_message(msg=msg)

    # Override
    def deserialize_message(self, data: bytes) -> Optional[ReliableMessage]:
        if data is None or len(data) < 2:
            # message data error
            return None
        return super().deserialize_message(data=data)

    # Override
    def verify_message(self, msg: ReliableMessage) -> Optional[SecureMessage]:
        if not self._check_reliable_message_sender(msg=msg):
            # sender not ready
            self.warning(msg='sender not ready: %s' % msg.sender)
            return None
        if not self._check_reliable_message_receiver(msg=msg):
            # receiver (group) not ready
            self.warning(msg='receiver not ready: %s' % msg.receiver)
            return None
        return super().verify_message(msg=msg)


def get_facebook(packer: MessagePacker):
    barrack = packer.facebook
    return barrack


def get_messenger(packer: MessagePacker):
    transceiver = packer.messenger
    from .messenger import CommonMessenger
    assert isinstance(transceiver, CommonMessenger), 'messenger error: %s' % transceiver
    return transceiver
