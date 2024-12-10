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

from typing import List

from dimsdk import DateTime
from dimsdk import EntityType
from dimsdk import InstantMessage, SecureMessage, ReliableMessage
from dimsdk import Content, TextContent
from dimsdk import ReceiptCommand
from dimsdk import ContentProcessorCreator

from ..common import HandshakeCommand
from ..common import CommonMessenger
from ..common import CommonMessageProcessor

from .cpu import ClientContentProcessorCreator

from .archivist import ClientArchivist


class ClientMessageProcessor(CommonMessageProcessor):

    @property
    def messenger(self) -> CommonMessenger:
        transceiver = super().messenger
        assert isinstance(transceiver, CommonMessenger), 'messenger error: %s' % transceiver
        return transceiver

    @property
    def archivist(self) -> ClientArchivist:
        db = self.facebook.archivist
        assert isinstance(db, ClientArchivist), 'client archivist error: %s' % db
        return db

    # Override
    async def process_secure_message(self, msg: SecureMessage, r_msg: ReliableMessage) -> List[SecureMessage]:
        try:
            return await super().process_secure_message(msg=msg, r_msg=r_msg)
        except Exception as error:
            self.error(msg='failed to process message: %s -> %s, %s' % (msg.sender, msg.receiver, error))
            return []

    # Override
    async def process_instant_message(self, msg: InstantMessage, r_msg: ReliableMessage) -> List[InstantMessage]:
        responses = await super().process_instant_message(msg=msg, r_msg=r_msg)
        if not await self._save_instant_message(msg=msg):
            self.error(msg='failed to save instant message: %s -> %s' % (msg.sender, msg.receiver))
            return []
        return responses

    async def _save_instant_message(self, msg: InstantMessage) -> bool:
        self.info(msg='TODO: saving instant message: %s -> %s' % (msg.sender, msg.receiver))
        return True

    # private
    async def _check_group_times(self, content: Content, r_msg: ReliableMessage) -> bool:
        group = content.group
        if group is None:
            return False
        else:
            facebook = self.facebook
            archivist = self.archivist
        now = DateTime.now()
        doc_updated = False
        mem_updated = False
        # check group document time
        last_doc_time = r_msg.get_datetime(key='GDT', default=None)
        if last_doc_time is not None:
            if last_doc_time.after(now):
                # calibrate the clock
                last_doc_time = now
            doc_updated = archivist.set_last_document_time(identifier=group, last_time=last_doc_time)
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
            mem_updated = archivist.set_last_group_history_time(group=group, last_time=last_his_time)
            # check whether needs update
            if mem_updated:
                archivist.set_last_active_member(member=r_msg.sender, group=group)
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

    # Override
    def _create_creator(self) -> ContentProcessorCreator:
        return ClientContentProcessorCreator(facebook=self.facebook, messenger=self.messenger)
