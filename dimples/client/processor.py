# -*- coding: utf-8 -*-
# ==============================================================================
# MIT License
#
# Copyright (c) 2021 Albert Moky
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
    Client extensions for MessageProcessor
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
"""

from typing import Optional, List

from dimsdk import DateTime
from dimsdk import EntityType
from dimsdk import ReliableMessage
from dimsdk import Content, TextContent
from dimsdk import ReceiptCommand
from dimsdk import ContentProcessorCreator

from ..common import HandshakeCommand
from ..common import CommonFacebook, CommonMessenger
from ..common import CommonMessageProcessor


class ClientMessageProcessor(CommonMessageProcessor):

    @property
    def facebook(self) -> Optional[CommonFacebook]:
        barrack = super().facebook
        assert isinstance(barrack, CommonFacebook), 'facebook error: %s' % barrack
        return barrack

    @property
    def messenger(self) -> Optional[CommonMessenger]:
        transceiver = super().messenger
        assert isinstance(transceiver, CommonMessenger), 'messenger error: %s' % transceiver
        return transceiver

    # Override
    def _create_creator(self, facebook: CommonFacebook, messenger: CommonMessenger) -> ContentProcessorCreator:
        from .cpu import ClientContentProcessorCreator
        return ClientContentProcessorCreator(facebook=facebook, messenger=messenger)

    # private
    async def _check_group_times(self, content: Content, r_msg: ReliableMessage) -> bool:
        group = content.group
        if group is None:
            return False
        else:
            facebook = self.facebook
            checker = facebook.checker
        now = DateTime.now()
        doc_updated = False
        mem_updated = False
        # check group document time
        last_doc_time = r_msg.get_datetime(key='GDT', default=None)
        if last_doc_time is not None:
            if last_doc_time.after(now):
                # calibrate the clock
                last_doc_time = now
            doc_updated = checker.set_last_document_time(identifier=group, now=last_doc_time)
            # check whether needs update
            if doc_updated:
                self.info(msg='checking for new bulletin: %s' % group)
                await facebook.get_documents(identifier=group)
        # check group history time
        last_his_time = r_msg.get_datetime(key='GHT', default=None)
        if last_his_time is not None:
            if last_his_time.after(now):
                # calibrate the clock
                last_his_time = now
            mem_updated = checker.set_last_group_history_time(identifier=group, now=last_his_time)
            # check whether needs update
            if mem_updated:
                checker.set_last_active_member(member=r_msg.sender, group=group)
                self.info(msg='checking for group members: %s' % group)
                await facebook.get_members(identifier=group)
        # OK
        return doc_updated or mem_updated

    # Override
    async def process_content(self, content: Content, r_msg: ReliableMessage) -> List[Content]:
        responses = await super().process_content(content=content, r_msg=r_msg)
        # check group document & history times from the message
        # to make sure the group info synchronized
        await self._check_group_times(content=content, r_msg=r_msg)
        # check responses
        if len(responses) == 0:
            # respond nothing
            return responses
        elif isinstance(responses[0], HandshakeCommand):
            # urgent command
            return responses
        sender = r_msg.sender
        receiver = r_msg.receiver
        user = await self.facebook.select_user(receiver=receiver)
        if user is None:
            # assert False, 'receiver error: %s' % receiver
            return responses
        receiver = user.identifier
        messenger = self.messenger
        # check responses
        from_bots = sender.type == EntityType.STATION or sender.type == EntityType.BOT
        for res in responses:
            if res is None:
                # should not happen
                continue
            elif isinstance(res, ReceiptCommand):
                if from_bots:
                    # no need to respond receipt to station
                    self.info(msg='drop receipt to %s, origin msg time=[%s]' % (sender, r_msg.time))
                    continue
            elif isinstance(res, TextContent):
                if from_bots:
                    # no need to respond text message to station
                    self.info(msg='drop text to %s, origin time=[%s], text=%s' % (sender, r_msg.time, res.text))
                    continue
            # normal response
            await messenger.send_content(sender=receiver, receiver=sender, content=res, priority=1)
        # DON'T respond to station directly
        return []
