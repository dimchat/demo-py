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
from typing import Optional, List

from dimsdk import EncryptKey
from dimsdk import ID
from dimsdk import ReceiptCommand, DocumentCommand
from dimsdk import InstantMessage, SecureMessage, ReliableMessage
from dimsdk import MessagePacker, MessageHelper

from ..utils import Logging

from .compat import fix_meta_attachment
from .compat import fix_receipt_command
from .compat import fix_document_command

from .facebook import CommonFacebook
from .messenger import CommonMessenger


class CommonMessagePacker(MessagePacker, Logging, ABC):

    @property
    def facebook(self) -> CommonFacebook:
        barrack = super().facebook
        assert isinstance(barrack, CommonFacebook), 'barrack error: %s' % barrack
        return barrack

    @property
    def messenger(self) -> CommonMessenger:
        transceiver = super().messenger
        assert isinstance(transceiver, CommonMessenger), 'transceiver error: %s' % transceiver
        return transceiver

    # protected
    def _visa_key(self, user: ID) -> Optional[EncryptKey]:
        """ for checking whether user's ready """
        key = self.facebook.public_key_for_encryption(identifier=user)
        if key is not None:
            # user is ready
            return key
        # user not ready, try to query document for it
        if self.messenger.query_document(identifier=user):
            self.info(msg='querying document for user: %s' % user)

    # protected
    def _members(self, group: ID) -> List[ID]:
        """ for checking whether group's ready """
        # check document
        doc = self.facebook.bulletin(identifier=group)
        if doc is None:
            # group not ready, try to query document for it
            if self.messenger.query_document(identifier=group):
                self.info(msg='querying document for group: %s' % group)
            return []
        # check members
        members = self.facebook.members(identifier=group)
        if len(members) == 0:
            # group not ready, try to query members for it
            if self.messenger.query_members(identifier=group):
                self.info(msg='querying members for group: %s' % group)
        return members

    # protected
    def _check_reliable_message_sender(self, msg: ReliableMessage) -> bool:
        """ Check sender before verifying received message """
        sender = msg.sender
        assert sender.is_user, 'sender error: %s' % sender
        # check sender's meta & document
        visa = MessageHelper.get_visa(msg=msg)
        if visa is not None:
            # first handshake?
            assert visa.identifier == sender, 'visa ID not match: %s => %s' % (sender, visa)
            # assert Meta.match_id(meta=msg.meta, identifier=sender), 'meta error: %s' % msg
            return visa.identifier == sender
        elif self._visa_key(user=sender) is not None:
            # sender is OK
            return True
        # sender not ready, suspend message for waiting document
        error = {
            'message': 'verify key not found',
            'user': str(sender),
        }
        self.messenger.suspend_reliable_message(msg=msg, error=error)  # msg['error'] = error
        return False

    # protected
    def _check_reliable_message_receiver(self, msg: ReliableMessage) -> bool:
        receiver = msg.receiver
        # check group
        group = ID.parse(identifier=msg.get('group'))
        if group is None and receiver.is_group:
            # Transform:
            #     (B) => (J)
            #     (D) => (G)
            group = receiver
        if group is None or group.is_broadcast:
            # A, C - personal message (or hidden group message)
            #     the packer will call the facebook to select a user from local
            #     for this receiver, if no user matched (private key not found),
            #     this message will be ignored;
            # E, F, G - broadcast group message
            #     broadcast message is not encrypted, so it can be read by anyone.
            return True
        # H, J, K - group message
        #     check for received group message
        members = self._members(group=group)
        if len(members) > 0:
            # group is ready
            return True
        # group not ready, suspend message for waiting members
        error = {
            'message': 'group not ready',
            'group': str(receiver),
        }
        self.messenger.suspend_reliable_message(msg=msg, error=error)  # msg['error'] = error
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
        self.messenger.suspend_instant_message(msg=msg, error=error)  # msg['error'] = error
        return False

    # Override
    def encrypt_message(self, msg: InstantMessage) -> Optional[SecureMessage]:
        # 1. check contact info
        # 2. check group members info
        if not self._check_instant_message_receiver(msg=msg):
            # receiver not ready
            self.warning(msg='receiver not ready: %s' % msg.receiver)
            return None
        content = msg.content
        if isinstance(content, ReceiptCommand):
            # compatible with v1.0
            fix_receipt_command(content=content)
        return super().encrypt_message(msg=msg)

    # Override
    def decrypt_message(self, msg: SecureMessage) -> Optional[InstantMessage]:
        i_msg = super().decrypt_message(msg=msg)
        if i_msg is not None:
            content = i_msg.content
            if isinstance(content, ReceiptCommand):
                # compatible with v1.0
                fix_receipt_command(content=content)
            elif isinstance(content, DocumentCommand):
                # compatible with v1.0
                fix_document_command(content=content)
        return i_msg

    # Override
    def verify_message(self, msg: ReliableMessage) -> Optional[SecureMessage]:
        # 1. check sender's meta
        if not self._check_reliable_message_sender(msg=msg):
            # sender not ready
            self.warning(msg='sender not ready: %s' % msg.sender)
            return None
        # 2. check receiver/group with local user
        if not self._check_reliable_message_receiver(msg=msg):
            # receiver (group) not ready
            self.warning(msg='receiver not ready: %s' % msg.receiver)
            return None
        return super().verify_message(msg=msg)

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
        # elif not (data.startswith(b'{') and data.endswith(b'}')):
        #     # only support JsON format now
        #     return None
        msg = super().deserialize_message(data=data)
        if msg is not None:
            fix_meta_attachment(msg=msg)
        return msg

    # Override
    def serialize_message(self, msg: ReliableMessage) -> bytes:
        fix_meta_attachment(msg=msg)
        return super().serialize_message(msg=msg)
