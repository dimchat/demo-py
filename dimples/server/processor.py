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
    Server extensions for MessageProcessor
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
"""

from typing import Optional, List

from dimsdk import EntityType, ID, ANYONE, EVERYONE
from dimsdk import Station
from dimsdk import InstantMessage, ReliableMessage
from dimsdk import Envelope
from dimsdk import Content
from dimsdk import TextContent, ReceiptCommand
from dimsdk import ContentProcessorCreator

from ..common import CommonFacebook, CommonMessenger
from ..common import CommonMessageProcessor

from .cpu import AnsCommandProcessor
from .cpu import ServerContentProcessorCreator

from .dispatcher import Dispatcher


class ServerMessageProcessor(CommonMessageProcessor):

    @property
    def facebook(self) -> CommonFacebook:
        barrack = super().facebook
        assert isinstance(barrack, CommonFacebook), 'facebook error: %s' % barrack
        return barrack

    @property
    def messenger(self) -> CommonMessenger:
        transceiver = super().messenger
        assert isinstance(transceiver, CommonMessenger), 'messenger error: %s' % transceiver
        return transceiver

    # Override
    def _create_creator(self, facebook: CommonFacebook, messenger: CommonMessenger) -> ContentProcessorCreator:
        return ServerContentProcessorCreator(facebook=facebook, messenger=messenger)

    # Override
    async def process_reliable_message(self, msg: ReliableMessage) -> List[ReliableMessage]:
        messenger = self.messenger
        session = messenger.session
        current = await self.facebook.current_user
        station = current.identifier
        receiver = msg.receiver
        #
        #  0. verify message
        #
        s_msg = await messenger.verify_message(msg=msg)
        if s_msg is None:
            # TODO: suspend and waiting for sender's meta if not exists
            return []
        #
        #  1. check receiver
        #
        if receiver != station and receiver != Station.ANY and receiver != ANYONE:
            # message not for this station, check session for delivering
            assert session.identifier is not None and session.active, 'user not login: %s' % msg.sender
            # session is active and user login success
            # if sender == session.ID,
            #   we can trust this message an no need to verify it;
            # else if sender is a neighbor station,
            #   we can trust it too;
            if receiver == Station.EVERY or receiver == EVERYONE:
                # broadcast message (to neighbor stations)
                # e.g.: 'stations@everywhere', 'everyone@everywhere'
                await self._broadcast_message(msg=msg, station=station)
                # if receiver == 'everyone@everywhere':
                #     broadcast message to all destinations,
                #     current station is it's receiver too.
            elif receiver.is_broadcast:
                # broadcast message (to station bots)
                # e.g.: 'archivist@anywhere', 'announcer@anywhere', 'monitor@anywhere', ...
                await self._broadcast_message(msg=msg, station=station)
                return []
            elif receiver.is_group:
                # encrypted group messages should be sent to the group assistant,
                # the station will never process these messages.
                await self._split_group_message(msg=msg, station=station)
                return []
            else:
                # this message is not for current station,
                # deliver to the real receiver and respond to sender
                return await self._deliver_message(msg=msg)
        # 2. process message
        responses = await messenger.process_secure_message(msg=s_msg, r_msg=msg)
        if len(responses) == 0:
            # nothing to respond
            return []
        # 3. sign message
        messages = []
        for res in responses:
            signed = await messenger.sign_message(msg=res)
            if signed is not None:
                messages.append(signed)
        return messages
        # TODO: override to deliver to the receiver when catch exception "receiver error ..."

    async def _broadcast_message(self, msg: ReliableMessage, station: ID):
        """ broadcast message to actual recipients """
        sender = msg.sender
        receiver = msg.receiver
        assert receiver.is_broadcast, 'broadcast message error: %s -> %s' % (sender, receiver)
        self.info(msg='broadcast message %s -> %s (%s)' % (sender, receiver, msg.group))
        if receiver.is_user:
            # broadcast message to station bots
            # e.g.: 'archivist@anywhere', 'announcer@anywhere', 'monitor@anywhere', ...
            name = receiver.name
            assert name is not None and name != 'station' and name != 'anyone', 'receiver error: %s' % receiver
            bot = AnsCommandProcessor.ans_id(name=name)
            if bot is None:
                self.warning(msg='failed to get receiver: %s' % receiver)
                return False
            elif bot == sender:
                self.warning(msg='skip cycled message: %s -> %s' % (sender, receiver))
                return False
            elif bot == station:
                self.warning(msg='skip current station: %s -> %s' % (sender, receiver))
                return False
            else:
                self.info(msg='forward to bot: %s -> %s' % (name, bot))
                receiver = bot
        else:
            # TODO: broadcast group?
            pass
        # deliver by dispatcher
        dispatcher = Dispatcher()
        await dispatcher.deliver_message(msg=msg, receiver=receiver)

    async def _split_group_message(self, msg: ReliableMessage, station: ID):
        """ redirect group message to assistant """
        sender = msg.sender
        receiver = msg.receiver
        self.error(msg='group message should not send to station: %s, %s -> %s' % (station, sender, receiver))

    async def _deliver_message(self, msg: ReliableMessage) -> List[ReliableMessage]:
        messenger = self.messenger
        current = await self.facebook.current_user
        sid = current.identifier
        sender = msg.sender
        receiver = msg.receiver
        # deliver
        dispatcher = Dispatcher()
        responses = await dispatcher.deliver_message(msg=msg, receiver=receiver)
        assert len(responses) > 0, 'should not happen'
        messages = []
        for res in responses:
            r_msg = await pack_message(content=res, sender=sid, receiver=sender, messenger=messenger)
            if r_msg is None:
                assert False, 'failed to send respond to: %s' % sender
            else:
                messages.append(r_msg)
        return messages

    # Override
    async def process_content(self, content: Content, r_msg: ReliableMessage) -> List[Content]:
        # process first
        responses = await super().process_content(content=content, r_msg=r_msg)
        # check responses
        contents = []
        sender = r_msg.sender
        from_station = sender.type == EntityType.STATION
        for res in responses:
            if res is None:
                # should not happen
                continue
            elif isinstance(res, ReceiptCommand):
                if from_station:
                    # no need to respond receipt to station
                    self.info(msg='drop receipt to %s, origin msg time=[%s]' % (sender, r_msg.time))
                    continue
            elif isinstance(res, TextContent):
                if from_station:
                    # no need to respond text message to station
                    self.info(msg='drop text to %s, origin time=[%s], text=%s' % (sender, r_msg.time, res.text))
                    continue
            contents.append(res)
        # OK
        return contents


async def pack_message(content: Content, sender: ID, receiver: ID,
                       messenger: CommonMessenger) -> Optional[ReliableMessage]:
    envelope = Envelope.create(sender=sender, receiver=receiver)
    i_msg = InstantMessage.create(head=envelope, body=content)
    s_msg = await messenger.encrypt_message(msg=i_msg)
    if s_msg is not None:
        return await messenger.sign_message(msg=s_msg)
