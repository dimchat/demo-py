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

from dimsdk import InstantMessage, SecureMessage, ReliableMessage
from dimsdk import DocumentCommand
from dimsdk import MessagePacker

from ..common import CommonFacebook, CommonMessenger


class ServerMessagePacker(MessagePacker):

    @property
    def facebook(self) -> CommonFacebook:
        barrack = super().facebook
        assert isinstance(barrack, CommonFacebook), 'facebook error: %s' % barrack
        return barrack

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

    # Override
    def decrypt_message(self, msg: SecureMessage) -> Optional[InstantMessage]:
        try:
            return super().decrypt_message(msg=msg)
        except AssertionError as error:
            err_msg = '%s' % error
            # check exception thrown by DKD: chat.dim.dkd.EncryptedMessage.decrypt()
            if err_msg.find('failed to decrypt key in msg') < 0:
                raise error
            # visa.key expired?
            # send new visa to the sender
            current = self.facebook.current_user
            uid = current.identifier
            visa = current.visa
            assert visa is not None and visa.valid, 'user visa error: %s' % current
            cmd = DocumentCommand.response(document=visa, identifier=uid)
            messenger = self.messenger
            assert isinstance(messenger, CommonMessenger), 'messenger error: %s' % messenger
            messenger.send_content(sender=uid, receiver=msg.sender, content=cmd)
