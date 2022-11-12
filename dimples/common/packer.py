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
    Common extensions for MessagePacker
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
"""
from typing import Optional

from dimsdk import base64_encode, sha256
from dimsdk import SymmetricKey
from dimsdk import InstantMessage, SecureMessage, ReliableMessage
from dimsdk import DocumentCommand
from dimsdk import Messenger, MessagePacker

from .messenger import CommonMessenger


class CommonPacker(MessagePacker):

    # Override
    def serialize_message(self, msg: ReliableMessage) -> bytes:
        attach_key_digest(msg=msg, messenger=self.messenger)
        return super().serialize_message(msg=msg)

    # Override
    def deserialize_message(self, data: bytes) -> Optional[ReliableMessage]:
        if data is None or len(data) < 2:
            # message data error
            return None
        return super().deserialize_message(data=data)

    # Override
    def sign_message(self, msg: SecureMessage) -> ReliableMessage:
        if isinstance(msg, ReliableMessage):
            # already signed
            return msg
        return super().sign_message(msg=msg)

    # # Override
    # def encrypt_message(self, msg: InstantMessage) -> Optional[SecureMessage]:
    #     # make sure visa.key exists before encrypting message
    #     s_msg = super().encrypt_message(msg=msg)
    #     receiver = msg.receiver
    #     if receiver.is_group:
    #         # reuse group message keys
    #         key = self.messenger.cipher_key(sender=msg.sender, receiver=receiver)
    #         key['reused'] = True
    #     # TODO: reuse personal message key?
    #     return s_msg

    # Override
    def decrypt_message(self, msg: SecureMessage) -> Optional[InstantMessage]:
        try:
            return super().decrypt_message(msg=msg)
        except AssertionError as error:
            err_msg = '%s' % error
            # check exception thrown by DKD: chat.dim.dkd.EncryptedMessage.decrypt()
            if err_msg.find('failed to decrypt key in msg') >= 0:
                # visa.key expired?
                # send new visa to the sender
                user = self.facebook.current_user
                visa = user.visa
                assert visa is not None and visa.valid, 'user visa error: %s' % user
                cmd = DocumentCommand.response(document=visa, identifier=user.identifier)
                messenger = self.messenger
                assert isinstance(messenger, CommonMessenger), 'messenger error: %s' % messenger
                messenger.send_content(sender=user.identifier, receiver=msg.sender, content=cmd)
            else:
                raise error


def attach_key_digest(msg: ReliableMessage, messenger: Messenger):
    # check message delegate
    if msg.delegate is None:
        msg.delegate = messenger
    # check msg.key
    if msg.encrypted_key is not None:
        # 'key' exists
        return
    # check msg.keys
    keys = msg.encrypted_keys
    if keys is None:
        keys = {}
    elif 'digest' in keys:
        # key digest already exists
        return
    # get key with direction
    sender = msg.sender
    group = msg.group
    if group is None:
        key = messenger.cipher_key(sender=sender, receiver=msg.receiver)
    else:
        key = messenger.cipher_key(sender=sender, receiver=group)
    digest = key_digest(key=key)
    if digest is None:
        # key error
        return
    keys['digest'] = digest
    msg['keys'] = keys


def key_digest(key: SymmetricKey) -> Optional[str]:
    """ get partially key data for digest """
    data = key.data
    if data is None or len(data) < 6:
        return None
    # get digest for the last 6 bytes of key.data
    pos = len(data) - 6
    digest = sha256(data[pos:])
    base64 = base64_encode(digest)
    # get last 8 chars as key digest
    pos = len(base64) - 8
    return base64[pos:]
