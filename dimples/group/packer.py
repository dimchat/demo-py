# -*- coding: utf-8 -*-
#
#   DIM-SDK : Decentralized Instant Messaging Software Development Kit
#
#                                Written in 2023 by Moky <albert.moky@gmail.com>
#
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

from typing import Optional, List

from dimsdk import ID, ANYONE
from dimsdk import Content, Envelope
from dimsdk import InstantMessage, ReliableMessage

from .delegate import TripletsHelper


class GroupPacker(TripletsHelper):

    async def pack_message(self, content: Content, sender: ID) -> Optional[ReliableMessage]:
        """ Pack as broadcast message """
        envelope = Envelope.create(sender=sender, receiver=ANYONE)
        msg = InstantMessage.create(head=envelope, body=content)
        msg.set_string(key='group', value=content.group)  # expose group ID
        return await self.encrypt_sign_message(msg=msg)

    async def encrypt_sign_message(self, msg: InstantMessage) -> Optional[ReliableMessage]:
        messenger = self.messenger
        # encrypt for receiver
        s_msg = await messenger.encrypt_message(msg=msg)
        if s_msg is None:
            self.error(msg='failed to encrypt message: %s => %s, %s' % (msg.sender, msg.receiver, msg.get('group')))
            return None
        # sign for sender
        r_msg = await messenger.sign_message(msg=s_msg)
        if r_msg is None:
            self.error(msg='failed to sign message: %s => %s, %s' % (msg.sender, msg.receiver, msg.get('group')))
            return None
        # OK
        return r_msg

    def split_instant_message(self, msg: InstantMessage, members: List[ID]) -> List[InstantMessage]:
        messages = []
        sender = msg.sender
        for receiver in members:
            if sender == receiver:
                self.info(msg='skip cycled message: %s, %s' % (receiver, msg.group))
                continue
            else:
                self.info(msg='split group message for member: %s' % receiver)
            info = msg.copy_dictionary(deep_copy=False)
            # Copy the content to avoid conflicts caused by modifications
            # by different processes.
            # Notice: there is no need to use deep copying here.
            info['content'] = msg.content.copy_dictionary(deep_copy=False)
            # replace 'receiver' with member ID
            info['receiver'] = str(receiver)
            item = InstantMessage.parse(msg=info)
            if item is None:
                self.error(msg='failed to repack message: %s' % receiver)
                continue
            messages.append(item)
        return messages

    def split_reliable_message(self, msg: ReliableMessage, members: List[ID]) -> List[ReliableMessage]:
        messages = []
        sender = msg.sender
        assert 'key' not in msg, 'should not happen'
        keys = msg.encrypted_keys
        if keys is None:
            keys = {}
            # TODO: get key digest
        for receiver in members:
            if sender == receiver:
                self.info(msg='skip cycled message: %s, %s' % (receiver, msg.group))
                continue
            else:
                self.info(msg='split group message for member: %s' % receiver)
            info = msg.copy_dictionary(deep_copy=False)
            # replace 'receiver' with member ID
            info['receiver'] = str(receiver)
            # fetch encrypted key data
            info.pop('keys', None)
            base64 = keys.get(str(receiver))
            if base64 is not None:
                info['key'] = base64
            item = ReliableMessage.parse(msg=info)
            if item is None:
                self.error(msg='failed to repack message: %s' % receiver)
                continue
            messages.append(item)
        return messages
