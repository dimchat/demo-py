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
from typing import Optional, List

from dimsdk import ID
from dimsdk import ContentType, TextContent, FileContent
from dimsdk import InstantMessage, SecureMessage, ReliableMessage

from ..utils import get_msg_sig
from ..common import CommonFacebook
from ..common import CommonMessagePacker

from .checkpoint import Checkpoint


class ClientMessagePacker(CommonMessagePacker):

    @property
    def facebook(self) -> Optional[CommonFacebook]:
        barrack = super().facebook
        assert isinstance(barrack, CommonFacebook), 'barrack error: %s' % barrack
        return barrack

    # protected
    async def _get_members(self, group: ID) -> List[ID]:
        """ for checking whether group's ready """
        db = self.facebook
        return await db.get_members(identifier=group)

    # Override
    async def _check_receiver(self, msg: InstantMessage) -> bool:
        receiver = msg.receiver
        if receiver.is_broadcast:
            # broadcast message
            return True
        elif receiver.is_user:
            # check user's meta & document
            return await super()._check_receiver(msg=msg)
        #
        #   check group's meta & members
        #
        members = await self._get_members(group=receiver)
        if len(members) == 0:
            # group not ready, suspend message for waiting meta/members
            error = {
                'message': 'group not ready',
                'group': str(receiver),
            }
            self.suspend_instant_message(msg=msg, error=error)
            return False
        #
        #   check group members' visa key
        #
        waiting = []
        for item in members:
            if await self._visa_key(user=item) is None:
                # member not ready
                waiting.append(item)
        if len(waiting) == 0:
            # all members' visa keys exist
            return True
        # member(s) not ready, suspend message for waiting document
        error = {
            'message': 'encrypt keys not found',
            'group': str(receiver),
            'members': ID.revert(identifiers=waiting),
        }
        self.suspend_instant_message(msg=msg, error=error)
        # perhaps some members have already disappeared,
        # although the packer will query document when the member's visa key is not found,
        # but the station will never respond with the right document,
        # so we must return true here to let the messaging continue;
        # when the member's visa is responded, we should send the suspended message again.
        return len(waiting) < len(members)

    # protected
    async def _check_group(self, msg: ReliableMessage) -> bool:
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
        members = await self._get_members(group=group)
        if len(members) > 0:
            # group is ready
            return True
        # group not ready, suspend message for waiting members
        error = {
            'message': 'group not ready',
            'group': str(receiver),
        }
        self.suspend_reliable_message(msg=msg, error=error)  # msg['error'] = error
        return False

    # Override
    async def verify_message(self, msg: ReliableMessage) -> Optional[SecureMessage]:
        # check receiver/group with local user
        if not await self._check_group(msg=msg):
            # receiver (group) not ready
            self.warning(msg='receiver not ready: %s' % msg.receiver)
            return None
        return await super().verify_message(msg=msg)

    # Override
    async def deserialize_message(self, data: bytes) -> Optional[ReliableMessage]:
        msg = await super().deserialize_message(data=data)
        if msg is not None and self._message_duplicated(msg=msg):
            msg = None
        return msg

    def _message_duplicated(self, msg: ReliableMessage) -> bool:
        cp = Checkpoint()
        if cp.duplicated(msg=msg):
            sig = get_msg_sig(msg=msg)
            self.warning(msg='drop duplicated message (%s): %s -> %s' % (sig, msg.sender, msg.receiver))
            return True

    # Override
    async def decrypt_message(self, msg: SecureMessage) -> Optional[InstantMessage]:
        try:
            i_msg = await super().decrypt_message(msg=msg)
        except AssertionError as error:
            err_msg = '%s' % error
            if err_msg.find('failed to decrypt message key') >= 0:
                # Exception from 'SecureMessagePacker::decrypt_message(msg, receiver)'
                self.warning(msg='decrypt message error: %s' % err_msg)
                # visa.key changed?
                # push my newest visa to the sender
                i_msg = None
            elif err_msg.find('receiver error') >= 0:
                # Exception from 'MessagePacker::decrypt_message(msg)'
                self.error(msg='decrypt message error: %s' % err_msg)
                # not for you?
                # just ignore it
                return None
            else:
                raise error
        if i_msg is None:
            # failed to decrypt message, visa.key changed?
            # 1. push new visa document to this message sender
            await self._push_visa(receiver=msg.sender)
            # 2. build 'failed' message
            i_msg = await self._build_failed_message(msg=msg)
        else:
            content = i_msg.content
            if isinstance(content, FileContent):
                if content.password is None and content.url is not None:
                    # now received file content with remote data,
                    # which must be encrypted before upload to CDN;
                    # so keep the password here for decrypting after downloaded.
                    pwd = self.messenger.get_decrypt_key(msg=msg)
                    content.password = pwd
        # OK
        return i_msg

    # protected
    async def _push_visa(self, receiver: ID) -> bool:
        facebook = self.facebook
        checker = facebook.checker
        # visa.key not updated?
        user = await facebook.current_user
        visa = await user.visa
        return await checker.send_visa(visa=visa, receiver=receiver)

    # protected
    async def _build_failed_message(self, msg: SecureMessage) -> Optional[InstantMessage]:
        sender = msg.sender
        group = msg.group
        msg_type = msg.type
        if msg_type == ContentType.COMMAND or type == ContentType.HISTORY:
            self.warning(msg='ignore message unable to decrypt (type=%s) from "%s"' % (msg_type, sender))
            return None
        # create text content
        content = TextContent.create(text='Failed to decrypt message.')
        content['template'] = 'Failed to decrypt message (type=${type}) from "${sender}".'
        content['replacements'] = {
            'type': msg_type,
            'sender': str(sender),
            'group': None if group is None else str(group)
        }
        if group is not None:
            content.group = group
        # pack instant message
        info = msg.copy_dictionary(deep_copy=False)
        info.pop('data', None)
        info['content'] = content.dictionary
        return InstantMessage.parse(msg=info)
