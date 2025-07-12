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
from typing import Optional, List, Dict

from dimsdk import EncryptKey
from dimsdk import ID
from dimsdk import InstantMessage, SecureMessage, ReliableMessage
from dimsdk import MessagePacker
from dimsdk import MessageUtils

from ..utils import Logging

from .facebook import CommonFacebook
from .messenger import CommonMessenger

from .queue import SuspendedMessageQueue


class CommonMessagePacker(MessagePacker, Logging, ABC):

    def __init__(self, facebook: CommonFacebook, messenger: CommonMessenger):
        super().__init__(facebook=facebook, messenger=messenger)
        self.__queue = SuspendedMessageQueue()

    @property  # Override
    def messenger(self) -> Optional[CommonMessenger]:
        transceiver = super().messenger
        assert isinstance(transceiver, CommonMessenger), 'transceiver error: %s' % transceiver
        return transceiver

    def suspend_reliable_message(self, msg: ReliableMessage, error: Dict):
        self.__queue.suspend_reliable_message(msg=msg, error=error)

    def suspend_instant_message(self, msg: InstantMessage, error: Dict):
        self.__queue.suspend_instant_message(msg=msg, error=error)

    def resume_reliable_messages(self) -> List[ReliableMessage]:
        return self.__queue.resume_reliable_messages()

    def resume_instant_messages(self) -> List[InstantMessage]:
        return self.__queue.resume_instant_messages()

    #
    #   Checking
    #

    # protected
    async def _visa_key(self, user: ID) -> Optional[EncryptKey]:
        """ for checking whether user's ready """
        db = self.facebook
        return await db.public_key_for_encryption(identifier=user)

    # protected
    async def _check_sender(self, msg: ReliableMessage) -> bool:
        """ Check sender before verifying received message """
        sender = msg.sender
        assert sender.is_user, 'sender error: %s' % sender
        # check sender's meta & document
        visa = MessageUtils.get_visa(msg=msg)
        if visa is not None:
            # first handshake?
            matched = visa.identifier == sender
            assert matched, 'visa ID not match: %s => %s' % (sender, visa)
            # assert Meta.match_id(meta=msg.meta, identifier=sender), 'meta error: %s' % msg
            return matched
        elif await self._visa_key(user=sender) is not None:
            # sender is OK
            return True
        # sender not ready, suspend message for waiting document
        error = {
            'message': 'verify key not found',
            'user': str(sender),
        }
        self.suspend_reliable_message(msg=msg, error=error)  # msg['error'] = error
        return False

    # protected
    async def _check_receiver(self, msg: InstantMessage) -> bool:
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
        elif await self._visa_key(user=receiver) is not None:
            # receiver is OK
            return True
        # receiver not ready, suspend message for waiting document
        error = {
            'message': 'encrypt key not found',
            'user': str(receiver),
        }
        self.suspend_instant_message(msg=msg, error=error)  # msg['error'] = error
        return False

    #
    #   Packing
    #

    # Override
    async def encrypt_message(self, msg: InstantMessage) -> Optional[SecureMessage]:
        # 1. check contact info
        # 2. check group members info
        if await self._check_receiver(msg=msg):
            # receiver is ready
            pass
        else:
            self.warning(msg='receiver not ready: %s' % msg.receiver)
            return None
        return await super().encrypt_message(msg=msg)

    # Override
    async def verify_message(self, msg: ReliableMessage) -> Optional[SecureMessage]:
        # 1. check receiver/group with local user
        # 2. check sender's meta
        if await self._check_sender(msg=msg):
            # sender is ready
            pass
        else:
            self.warning(msg='sender not ready: %s' % msg.sender)
            return None
        return await super().verify_message(msg=msg)

    # Override
    async def sign_message(self, msg: SecureMessage) -> ReliableMessage:
        if isinstance(msg, ReliableMessage):
            # already signed
            return msg
        return await super().sign_message(msg=msg)
