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
    Message Dispatcher
    ~~~~~~~~~~~~~~~~~~

    A dispatcher to decide which way to deliver message.
"""

from typing import Optional, Set, List

from dimsdk import EntityType, ID, EVERYONE
from dimsdk import Station
from dimsdk import Content, ReceiptCommand
from dimsdk import ReliableMessage

from ..utils import Singleton, Logging
from ..common import CommonFacebook
from ..common import MessageDBI, SessionDBI

from .checker import ServerChecker
from .push import PushCenter
from .deliver import MessageDeliver, session_push
from .dis_roamer import Roamer


@Singleton
class Dispatcher(Logging):

    def __init__(self):
        super().__init__()
        self.__facebook: Optional[CommonFacebook] = None
        self.__mdb: Optional[MessageDBI] = None
        self.__sdb: Optional[SessionDBI] = None
        # actually deliver worker
        self.__deliver: Optional[MessageDeliver] = None
        # roaming user receptionist
        self.__roamer: Optional[Roamer] = None

    @property
    def facebook(self) -> CommonFacebook:
        return self.__facebook

    @facebook.setter
    def facebook(self, barrack: CommonFacebook):
        self.__facebook = barrack

    #
    #   Database
    #

    @property
    def mdb(self) -> MessageDBI:
        return self.__mdb

    @mdb.setter
    def mdb(self, db: MessageDBI):
        self.__mdb = db

    @property
    def sdb(self) -> SessionDBI:
        return self.__sdb

    @sdb.setter
    def sdb(self, db: SessionDBI):
        self.__sdb = db

    #
    #   Message Deliver
    #

    @property
    def deliver(self) -> MessageDeliver:
        return self.__deliver

    @deliver.setter
    def deliver(self, worker: MessageDeliver):
        self.__deliver = worker

    #
    #   Roamer
    #

    @property
    def roamer(self) -> Roamer:
        return self.__roamer

    @roamer.setter
    def roamer(self, worker: Roamer):
        self.__roamer = worker

    def add_roaming(self, user: ID, station: ID) -> bool:
        """ Add roaming user with station """
        roamer = self.roamer
        return roamer.add_roaming(user=user, station=station)

    #
    #   Delivery
    #

    async def deliver_message(self, msg: ReliableMessage, receiver: ID) -> List[Content]:
        """
        Deliver message to destination

        :param msg:      message delivering
        :param receiver: message destination
        :return: responses
        """
        worker = self.deliver
        if receiver.is_group:
            # broadcast message to neighbor stations
            # e.g.: 'stations@everywhere', 'everyone@everywhere'
            return await self.__deliver_group_message(msg=msg, receiver=receiver)
        elif receiver.type == EntityType.STATION:
            # message to other stations
            # station won't roam to other station, so just push for it directly
            responses = await worker.redirect_message(msg=msg, neighbor=receiver)
        elif receiver.type == EntityType.BOT:
            # message to a bot
            # save message before trying to push
            await self.__save_reliable_message(msg=msg, receiver=receiver)
            responses = await worker.push_message(msg=msg, receiver=receiver)
        else:
            # message to user
            # save message before trying to push
            await self.__save_reliable_message(msg=msg, receiver=receiver)
            responses = await worker.push_message(msg=msg, receiver=receiver)
            if responses is None:
                # failed to push message, user not online and not roamed to other station,
                # push notification for the receiver
                center = PushCenter()
                center.push_notification(msg=msg)
        # OK
        if responses is None:
            # user not online, and not roaming to other station
            text = 'Message cached.'
            res = ReceiptCommand.create(text=text, envelope=msg.envelope)
            return [res]
        elif len(responses) == 0:
            # user roamed to other station, but bridge not found
            text = 'Message received.'
            res = ReceiptCommand.create(text=text, envelope=msg.envelope)
            return [res]
        else:
            # message delivered
            return responses

    async def __deliver_group_message(self, msg: ReliableMessage, receiver: ID) -> List[Content]:
        if receiver == Station.EVERY or receiver == EVERYONE:
            # broadcast message to neighbor stations
            # e.g.: 'stations@everywhere', 'everyone@everywhere'
            checker = self.facebook.checker
            assert isinstance(checker, ServerChecker), 'entity checker error: %s' % checker
            candidates = await checker.all_neighbors
            if len(candidates) == 0:
                self.warning(msg='failed to get neighbors: %s' % receiver)
                return []
            self.info(msg='forward to neighbor stations: %s -> %s' % (receiver, candidates))
            return await self.__broadcast_message(msg=msg, receiver=receiver, neighbors=candidates)
        else:
            self.warning(msg='unknown group: %s' % receiver)
            text = 'Group message not allow for this station'
            res = ReceiptCommand.create(text=text, envelope=msg.envelope)
            return [res]

    async def __broadcast_message(self, msg: ReliableMessage, receiver: ID, neighbors: Set[ID]) -> List[Content]:
        current = await self.facebook.current_user
        assert current is not None, 'failed to get current station'
        current = current.identifier
        #
        #  0. check recipients
        #
        new_recipients = set()
        old_recipients = msg.get('recipients')
        old_recipients = [] if old_recipients is None else ID.convert(old_recipients)
        for item in neighbors:
            if item == current:
                self.info(msg='skip current station: %s' % item)
                continue
            elif item in old_recipients:
                self.info(msg='skip exists station: %s' % item)
                continue
            self.info(msg='new neighbor station: %s' % item)
            new_recipients.add(item)
        # set 'recipients' in the msg to avoid the new recipients redirect it to same targets
        self.info(msg='append new recipients: %s, %s + %s' % (receiver, new_recipients, old_recipients))
        all_recipients = list(old_recipients) + list(new_recipients)
        msg['recipients'] = ID.revert(all_recipients)
        #
        #  1. push to neighbor stations directly
        #
        indirect_neighbors = set()
        for target in new_recipients:
            if await session_push(msg=msg, receiver=target) == 0:
                indirect_neighbors.add(target)
        # remove unsuccessful items
        for item in indirect_neighbors:
            new_recipients.discard(item)
        # update 'recipients' before redirect via bridge
        self.info(msg='update recipients: %s, %s + %s' % (receiver, new_recipients, old_recipients))
        all_recipients = list(old_recipients) + list(new_recipients)
        msg['recipients'] = ID.revert(all_recipients)
        #
        #  2. push to other neighbor stations via station bridge
        #
        worker = self.deliver
        await worker.redirect_message(msg=msg, neighbor=None)
        #
        #  OK
        #
        text = 'Message forwarded.'
        cmd = ReceiptCommand.create(text=text, envelope=msg.envelope)
        cmd['recipients'] = ID.revert(new_recipients)
        return [cmd]

    async def __save_reliable_message(self, msg: ReliableMessage, receiver: ID) -> bool:
        if receiver.type == EntityType.STATION or msg.sender.type == EntityType.STATION:
            # no need to save station message
            return False
        elif msg.receiver.is_broadcast:
            # no need to save broadcast message
            return False
        # save message in cache
        return await self.mdb.cache_reliable_message(msg=msg, receiver=receiver)
