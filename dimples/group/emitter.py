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

from dimsdk import ID
from dimsdk import InstantMessage, ReliableMessage
from dimsdk import ForwardContent, FileContent
from dimsdk import GroupCommand

from ..utils import Logging
from ..common import CommonFacebook, CommonMessenger

from .delegate import GroupDelegate
from .packer import GroupPacker


class GroupEmitter(Logging):

    #   NOTICE: group assistants (bots) can help the members to redirect messages
    #
    #       if members.length < POLYLOGUE_LIMIT,
    #           means it is a small polylogue group, let the members to split
    #           and send group messages by themselves, this can keep the group
    #           more secretive because no one else can know the group ID even;
    #       else,
    #           set 'assistants' in the bulletin document to tell all members
    #           that they can let the group bot to do the job for them.
    #
    POLYLOGUE_LIMIT = 32

    #   NOTICE: expose group ID to reduce encrypting time
    #
    #       if members.length < SECRET_GROUP_LIMIT,
    #           means it is a tiny group, you can choose to hide the group ID,
    #           that you can split and encrypt message one by one;
    #       else,
    #           you should expose group ID in the instant message level, then
    #           encrypt message by one symmetric key for this group, after that,
    #           split and send to all members directly.
    #
    SECRET_GROUP_LIMIT = 16

    def __init__(self, delegate: GroupDelegate):
        super().__init__()
        self.__delegate = delegate
        self.__packer = self._create_packer()

    def _create_packer(self) -> GroupPacker:
        """ override for customized packer """
        return GroupPacker(self.delegate)

    @property  # protected
    def delegate(self) -> GroupDelegate:
        return self.__delegate

    @property  # protected
    def packer(self) -> GroupPacker:
        return self.__packer

    @property  # protected
    def facebook(self) -> CommonFacebook:
        return self.delegate.facebook

    @property  # protected
    def messenger(self) -> CommonMessenger:
        return self.delegate.messenger

    # private
    async def _attach_group_times(self, group: ID, msg: InstantMessage) -> bool:
        if isinstance(msg.content, GroupCommand):
            # no need to attach times for group command
            return True
        facebook = self.facebook
        doc = await facebook.get_bulletin(identifier=group)
        if doc is None:
            self.error(msg='failed to get bulletin document for group: %s' % group)
            return False
        # attach group document time
        last_doc_time = doc.time
        if last_doc_time is None:
            self.error(msg='document error: %s' % doc)
            return False
        else:
            msg.set_datetime(key='GDT', value=last_doc_time)
        # attach group history time
        archivist = facebook.archivist
        last_his_time = await archivist.get_last_group_history_time(group=group)
        if last_his_time is None:
            self.error(msg='failed to get history time: %s' % group)
            return False
        else:
            msg.set_datetime(key='GHT', value=last_his_time)
        return True

    async def send_message(self, msg: InstantMessage, priority: int = 0) -> Optional[ReliableMessage]:
        content = msg.content
        group = content.group
        if group is None:
            self.error(msg='not a group message')
            return None
        assert msg.receiver == group, 'group message error: %s' % msg
        # attach group document & history times
        # for the receiver to check whether group info synchronized
        ok = await self._attach_group_times(group=group, msg=msg)
        if not ok:
            self.warning(msg='failed to attach group times: %s => %s' % (group, content))
        # TODO: if it's a file message
        #       please upload the file data first
        #       before calling this
        assert not isinstance(content, FileContent) or 'data' not in content, 'content error: %s' % content
        #
        #   1. check group bots
        #
        bots = await self.delegate.get_assistants(identifier=group)
        if len(bots) > 0:
            # group bots found, forward this message to any bot to let it split for me;
            # this can reduce my jobs.
            prime = bots[0]
            return await self.__forward_message(msg=msg, bot=prime, group=group, priority=priority)
        #
        #   2. check group members
        #
        members = await self.delegate.get_members(identifier=group)
        count = len(members)
        if count == 0:
            self.error(msg='failed to get members for group: %s' % group)
            return None
        # no 'assistants' found in group's bulletin document?
        # split group messages and send to all members one by one
        if count < self.SECRET_GROUP_LIMIT:
            # it is a tiny group, split this message before encrypting and signing,
            # then send this group message to all members one by one
            success = await self.__split_send_message(msg=msg, members=members, group=group, priority=priority)
            self.info(msg='split %d message(s) for group: %s' % (success, group))
        else:
            self.info(msg='splitting message for %d members of group: %s' % (len(members), group))
            # encrypt and sign this message first,
            # then split and send to all members one by one
            return await self.__disperse_message(msg=msg, members=members, group=group, priority=priority)

    async def __forward_message(self, msg: InstantMessage, bot: ID, group: ID,
                                priority: int = 0) -> Optional[ReliableMessage]:
        """ Encrypt & sign message, then forward to the bot """
        assert bot.is_user and group.is_group, 'ID error: %s, %s' % (bot, group)
        # NOTICE: because group assistant (bot) cannot be a member of the group, so
        #         if you want to send a group command to any assistant, you must
        #         set the bot ID as 'receiver' and set the group ID in content;
        #         this means you must send it to the bot directly.
        messenger = self.messenger
        #
        # group bots designated, let group bot to split the message, so
        # here must expose the group ID; this will cause the client to
        # use a "user-to-group" encrypt key to encrypt the message content,
        # this key will be encrypted by each member's public key, so
        # all members will received a message split by the group bot,
        # but the group bots cannot decrypt it.
        msg.set_string(key='group', value=group)
        #
        #   1. pack message
        #
        r_msg = await self.packer.encrypt_sign_message(msg=msg)
        if r_msg is None:
            self.error(msg='failed to encrypt & sign message: %s => %s' % (msg.sender, group))
            return None
        #
        #   2. forward the group message to any bot
        #
        content = ForwardContent.create(message=r_msg)
        _, out = await messenger.send_content(sender=None, receiver=bot, content=content, priority=priority)
        if out is None:
            self.error(msg='failed to forward message for group: %s, bot: %s' % (group, bot))
        # OK, return the forwarding message
        return r_msg

    async def __disperse_message(self, msg: InstantMessage, members: List[ID], group: ID,
                                 priority: int = 0) -> Optional[ReliableMessage]:
        """ Encrypt & sign message, then disperse to all members """
        assert group.is_group, 'group ID error: %s' % group
        # assert 'group' not in msg, 'should not happen'
        messenger = self.messenger
        # NOTICE: there are too many members in this group
        #         if we still hide the group ID, the cost will be very high.
        #     so,
        #         here I suggest to expose 'group' on this message's envelope
        #         to use a user-to-group password to encrypt the message content,
        #         and the actual receiver can get the decrypt key
        #         with the accurate direction: (sender -> group)
        msg.set_string(key='group', value=group)

        sender = msg.sender
        #
        #   1. pack message
        #
        r_msg = await self.packer.encrypt_sign_message(msg=msg)
        if r_msg is None:
            self.error(msg='failed to encrypt & sign message: %s => %s' % (sender, group))
            return None
        #
        #   2. split messages
        #
        messages = self.packer.split_reliable_message(msg=r_msg, members=members)
        for item in messages:
            receiver = item.receiver
            if sender == receiver:
                self.error(msg='cycled message: %s => %s, %s' % (sender, receiver, group))
                continue
            ok = await messenger.send_reliable_message(msg=item, priority=priority)
            if not ok:
                # assert ok, 'failed to send message: %s => %s, %s' % (sender, receiver, group)
                self.error(msg='failed to send message: %s => %s, %s' % (sender, receiver, group))
        # sent
        return r_msg

    async def __split_send_message(self, msg: InstantMessage, members: List[ID], group: ID, priority: int = 0) -> int:
        """ Split and send (encrypt + sign) group messages to all members one by one """
        assert group.is_group, 'group ID error: %s' % group
        assert 'group' not in msg, 'should not happen'
        messenger = self.messenger
        #
        # NOTICE: this is a tiny group
        #         I suggest NOT to expose the group ID to maximize its privacy,
        #         the cost is we cannot use a user-to-group password here;
        #         So the other members can only treat it as a personal message
        #         and use the user-to-user symmetric key to decrypt content,
        #         they can get the group ID after decrypted.
        #
        sender = msg.sender
        success = 0
        #
        #   1. split messages
        #
        messages = self.packer.split_instant_message(msg=msg, members=members)
        for item in messages:
            receiver = item.receiver
            if sender == receiver:
                self.error(msg='cycled message: %s => %s, %s' % (sender, receiver, group))
                continue
            #
            #   2. send message
            #
            r_msg = await messenger.send_instant_message(msg=item, priority=priority)
            if r_msg is None:
                self.error(msg='failed to send message: %s => %s, %s' % (sender, receiver, group))
                continue
            success += 1
        # done!
        return success
