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
from dimsdk import Facebook, Messenger
from dimsdk import ContentProcessorCreator

from ..common import HandshakeCommand
from ..common import CommonFacebook, CommonMessenger
from ..common import CommonMessageProcessor

from .cpu import AnsCommandProcessor

from .trace import TraceManager
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
    def _create_creator(self, facebook: Facebook, messenger: Messenger) -> ContentProcessorCreator:
        from .cpu import ServerContentProcessorCreator
        return ServerContentProcessorCreator(facebook=facebook, messenger=messenger)

    async def _is_traced(self, msg: ReliableMessage) -> bool:
        """ check & append current node in msg['traces'] """
        facebook = self.facebook
        current = await facebook.current_user
        node = current.identifier
        tm = TraceManager()
        is_traced = tm.is_traced(msg=msg, node=node)
        tm.add_node(msg=msg, node=node)
        return is_traced

    async def _check_duplicated(self, msg: ReliableMessage) -> bool:
        sender = msg.sender
        receiver = msg.receiver
        if await self._is_traced(msg=msg):
            # cycled message
            if sender.type == EntityType.STATION or receiver.type == EntityType.STATION:
                # ignore cycled station message
                self.warning(msg='drop cycled station message: %s -> %s' % (sender, receiver))
                return True
            elif receiver.is_broadcast:
                # ignore cycled broadcast message
                self.warning(msg='drop cycled broadcast message: %s -> %s' % (sender, receiver))
                return True
            self.warning(msg='cycled message: %s -> %s' % (sender, receiver))
            # TODO: check last time?

    async def _pretreatment(self, msg: ReliableMessage) -> Optional[List[ReliableMessage]]:
        facebook = self.facebook
        current = await facebook.current_user
        station = current.identifier
        receiver = msg.receiver
        if receiver == station:
            # message to this station
            # maybe a meta command, document command, etc ...
            return None
        elif receiver == Station.ANY or receiver == ANYONE:
            # if receiver == 'station@anywhere':
            #     it must be the first handshake without station ID;
            # if receiver == 'anyone@anywhere':
            #     it should be other plain message without encryption.
            return None
        # check session
        messenger = self.messenger
        session = messenger.session
        if session.identifier is None or not session.active:
            # not login?
            # 2.1. suspend this message for waiting handshake
            error = {
                'message': 'user not login',
            }
            messenger.suspend_reliable_message(msg=msg, error=error)
            # 2.2. ask client to handshake again (with session key)
            #      this message won't be delivered before handshake accepted
            command = HandshakeCommand.ask(session=session.session_key)
            command['force'] = True
            await messenger.send_content(content=command, sender=station, receiver=msg.sender, priority=-1)
            return []
        elif receiver == Station.EVERY or receiver == EVERYONE:
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

    # Override
    async def process_reliable_message(self, msg: ReliableMessage) -> List[ReliableMessage]:
        # 1. check valid
        if await self._check_duplicated(msg=msg):
            # duplicated
            return []
        # 2. check for redirecting
        responses = await self._pretreatment(msg=msg)
        if responses is not None:
            # redirected
            return responses
        # 3. process my message
        return await super().process_reliable_message(msg=msg)

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
