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

import weakref
from typing import Optional, Set, List, Dict

from startrek.types import Duration

from dimsdk import DateTime
from dimsdk import EntityType
from dimsdk import ID, Meta, Document, Bulletin
from dimsdk import Envelope
from dimsdk import ReceiptCommand
from dimsdk import GroupDataSource
from dimsdk import MetaUtils
from dimsdk import TwinsHelper

from ..utils import Logging, Singleton
from ..utils import Runner
from ..common import CommonFacebook, CommonMessenger
from ..common import CommonArchivist, AccountDBI


class GroupDelegate(TwinsHelper, GroupDataSource, Logging):

    def __init__(self, facebook: CommonFacebook, messenger: CommonMessenger):
        super().__init__(facebook=facebook, messenger=messenger)
        shared = SharedBotsManager()
        shared.set_messenger(messenger=messenger)

    @property  # Override
    def facebook(self) -> CommonFacebook:
        barrack = super().facebook
        assert isinstance(barrack, CommonFacebook), 'facebook error: %s' % barrack
        return barrack

    @property  # Override
    def messenger(self) -> CommonMessenger:
        transceiver = super().messenger
        assert isinstance(transceiver, CommonMessenger), 'messenger error: %s' % transceiver
        return transceiver

    async def build_group_name(self, members: List[ID]) -> str:
        count = len(members)
        if count > 0:
            facebook = self.facebook
            text = await facebook.get_name(identifier=members[0])
            for i in range(1, count):
                nickname = await facebook.get_name(identifier=members[i])
                if len(nickname) == 0:
                    continue
                text += ', %s' % nickname
                if len(text) > 32:
                    text = text[:28]
                    return '%s ...' % text
            # OK
            return text
        assert False, 'members should not be empty here'

    #
    #   Entity DataSource
    #

    # Override
    async def get_meta(self, identifier: ID) -> Optional[Meta]:
        return await self.facebook.get_meta(identifier=identifier)

    # Override
    async def get_documents(self, identifier: ID) -> List[Document]:
        return await self.facebook.get_documents(identifier=identifier)

    async def get_bulletin(self, identifier: ID) -> Optional[Bulletin]:
        assert identifier.is_group, 'group ID error: %s' % identifier
        return await self.facebook.get_bulletin(identifier)

    async def save_document(self, document: Document) -> bool:
        return await self.facebook.save_document(document=document)

    #
    #   Group DataSource
    #

    # Override
    async def get_founder(self, identifier: ID) -> Optional[ID]:
        assert identifier.is_group, 'group ID error: %s' % identifier
        return await self.facebook.get_founder(identifier=identifier)

    # Override
    async def get_owner(self, identifier: ID) -> Optional[ID]:
        assert identifier.is_group, 'group ID error: %s' % identifier
        return await self.facebook.get_owner(identifier=identifier)

    # Override
    async def get_members(self, identifier: ID) -> List[ID]:
        assert identifier.is_group, 'group ID error: %s' % identifier
        return await self.facebook.get_members(identifier=identifier)

    async def save_members(self, members: List[ID], group: ID) -> bool:
        assert group.is_group, 'group ID error: %s' % group
        return await self.facebook.save_members(members=members, group=group)

    #
    #   Group Assistants
    #

    # Override
    async def get_assistants(self, identifier: ID) -> List[ID]:
        assert identifier.is_group, 'group ID error: %s' % identifier
        man = SharedBotsManager()
        return await man.group_bots_manager.get_assistants(identifier)

    # noinspection PyMethodMayBeStatic
    async def get_fastest_assistant(self, identifier: ID) -> Optional[ID]:
        assert identifier.is_group, 'group ID error: %s' % identifier
        man = SharedBotsManager()
        return await man.group_bots_manager.get_fastest_assistant(identifier)

    # noinspection PyMethodMayBeStatic
    def set_common_assistants(self, bots: List[ID]) -> Optional[ID]:
        man = SharedBotsManager()
        return man.group_bots_manager.set_common_assistants(bots=bots)

    # noinspection PyMethodMayBeStatic
    def update_respond_time(self, content: ReceiptCommand, envelope: Envelope) -> bool:
        man = SharedBotsManager()
        return man.group_bots_manager.update_respond_time(content=content, envelope=envelope)

    #
    #   Administrators
    #

    async def get_administrators(self, group: ID) -> List[ID]:
        assert group.is_group, 'group ID error: %s' % group
        return await self.facebook.get_administrators(group=group)

    async def save_administrators(self, administrators: List[ID], group: ID) -> bool:
        assert group.is_group, 'group ID error: %s' % group
        return await self.facebook.save_administrators(administrators, group=group)

    #
    #   Membership
    #

    async def is_founder(self, user: ID, group: ID) -> bool:
        assert user.is_user and group.is_group, 'ID error: %s, %s' % (user, group)
        founder = await self.get_founder(identifier=group)
        if founder is not None:
            return founder == user
        # check member's public key with group's meta.key
        g_meta = await self.get_meta(identifier=group)
        m_meta = await self.get_meta(identifier=user)
        if g_meta is None or m_meta is None:
            self.warning(msg='failed to get meta for group: %s, user: %s' % (group, user))
            return False
        return MetaUtils.match_public_key(key=m_meta.public_key, meta=g_meta)

    async def is_owner(self, user: ID, group: ID) -> bool:
        assert user.is_user and group.is_group, 'ID error: %s, %s' % (user, group)
        owner = await self.get_owner(identifier=group)
        if owner is not None:
            return owner == user
        if group.type == EntityType.GROUP:
            # this is a polylogue
            return await self.is_founder(user=user, group=group)
        raise Exception('only polylogue so far')

    async def is_member(self, user: ID, group: ID) -> bool:
        assert user.is_user and group.is_group, 'ID error: %s, %s' % (user, group)
        members = await self.get_members(identifier=group)
        return user in members

    async def is_administrator(self, user: ID, group: ID) -> bool:
        assert user.is_user and group.is_group, 'ID error: %s, %s' % (user, group)
        admins = await self.get_administrators(group=group)
        return user in admins

    async def is_assistant(self, user: ID, group: ID) -> bool:
        assert user.is_user and group.is_group, 'ID error: %s, %s' % (user, group)
        bots = await self.get_assistants(identifier=group)
        return user in bots


class TripletsHelper(Logging):

    def __init__(self, delegate: GroupDelegate):
        super().__init__()
        self.__delegate = delegate

    @property
    def delegate(self) -> GroupDelegate:
        return self.__delegate

    @property
    def facebook(self) -> Optional[CommonFacebook]:
        return self.delegate.facebook

    @property
    def messenger(self) -> Optional[CommonMessenger]:
        return self.delegate.messenger

    @property
    def archivist(self) -> Optional[CommonArchivist]:
        facebook = self.facebook
        if facebook is not None:
            return facebook.archivist

    @property
    def database(self) -> Optional[AccountDBI]:
        facebook = self.facebook
        if facebook is not None:
            return facebook.database


# Singleton
class GroupBotsManager(Runner, Logging):

    def __init__(self):
        super().__init__(interval=Runner.INTERVAL_SLOW)
        self.__common_assistants: List[ID] = []
        self.__candidates: Set[ID] = set()             # bot IDs to be check
        self.__respond_times: Dict[ID, Duration] = {}  # bot IDs with respond time
        self.__transceiver = None

    @property
    def messenger(self) -> Optional[CommonMessenger]:
        ref = self.__transceiver
        if ref is not None:
            return ref()

    @messenger.setter
    def messenger(self, transceiver: CommonMessenger):
        self.__transceiver = None if transceiver is None else weakref.ref(transceiver)

    @property
    def facebook(self) -> Optional[CommonFacebook]:
        messenger = self.messenger
        if messenger is not None:
            return messenger.facebook

    def update_respond_time(self, content: ReceiptCommand, envelope: Envelope) -> bool:
        """
        When received receipt command from the bot
        update the speed of this bot.
        """
        # app = content['app']
        # if app is None:
        #     app = content['app_id']
        # if app != 'chat.dim.group.assistant':
        #     return False
        #
        #  1. check sender
        #
        sender = envelope.sender
        if sender.type != EntityType.BOT:
            return False
        origin = content.original_envelope
        if origin is None:
            return False
        original_receiver = origin.receiver
        if original_receiver != sender:
            return False
        #
        #  2. check send time
        #
        when = origin.time
        if when is None:
            return False
        duration = DateTime.now() - when
        if duration <= 0:
            return False
        #
        #  3. check duration
        #
        cached = self.__respond_times.get(sender)
        if cached is not None and cached <= duration:
            return False
        self.__respond_times[sender] = duration
        return True

    def set_common_assistants(self, bots: List[ID]):
        """
        When received new config from current Service Provider,
        set common assistants of this SP.
        """
        self.info(msg='add group bots: %s into %s' % (bots, self.__candidates))
        for item in bots:
            self.__candidates.add(item)
        self.__common_assistants = bots

    async def get_assistants(self, group: ID) -> List[ID]:
        facebook = self.facebook
        if facebook is None:
            bots = None
        else:
            bots = await facebook.get_assistants(identifier=group)
        if bots is None or len(bots) == 0:
            return self.__common_assistants
        for item in bots:
            self.__candidates.add(item)
        return bots

    async def get_fastest_assistant(self, group: ID) -> Optional[ID]:
        """ Get the fastest group bot """
        bots = await self.get_assistants(group=group)
        if bots is None or len(bots) == 0:
            self.warning(msg='group bots not found: %s' % group)
            return None
        prime = None
        prime_duration = None
        for item in bots:
            duration = self.__respond_times.get(item)
            if duration is None:
                self.info(msg='group bot not respond yet, ignore it: %s, %s' % (item, group))
                continue
            elif prime_duration is None:
                # first responded bot
                pass
            elif prime_duration < duration:
                self.info(msg='this bot %s is slower than %s, skip it, %s' % (item, prime, group))
                continue
            prime = item
            prime_duration = duration
        if prime is None:
            prime = bots[0]
            self.info(msg='no bot responded, take the first one: %s, %s' % (bots, group))
        else:
            self.info(msg='got the fastest bot with respond time: %s, %s, %s' % (prime_duration, prime, group))
        return prime

    def start(self):
        Runner.async_task(coro=self.run())

    # Override
    async def process(self) -> bool:
        facebook = self.facebook
        messenger = self.messenger
        if facebook is None or messenger is None:
            self.warning(msg='facebook/messenger not ready')
            return False
        #
        #  1. check session
        #
        session = messenger.session
        if session.session_key is None or not session.active:
            # not login yet
            return False
        #
        #  2. get visa
        #
        try:
            user = await facebook.current_user
            if user is None:
                self.error(msg='failed to get current user')
                return False
            visa = await user.visa
            if visa is None:
                self.error(msg='failed to get visa: %s' % user)
                return False
        except Exception as error:
            self.error(msg='failed to get current user visa: %s' % error)
            return False
        #
        #  3. check candidates
        #
        checker = facebook.checker
        if checker is None:
            self.warning(msg='entity checker not ready')
            return False
        bots = self.__candidates
        self.__candidates = set()
        for item in bots:
            if self.__respond_times.get(item) is not None:
                # no need to check again
                self.info(msg='group bot already responded: %s' % item)
                continue
            # no respond yet, try to push visa to the bot
            try:
                await checker.send_visa(visa=visa, receiver=item)
            except Exception as error:
                self.error(msg='failed to query assistant: %s, %s' % (item, error))


@Singleton
class SharedBotsManager:

    def __init__(self):
        super().__init__()
        man = GroupBotsManager()
        man.start()
        self.__bots_manager = man

    @property
    def group_bots_manager(self) -> GroupBotsManager:
        return self.__bots_manager

    def set_messenger(self, messenger: CommonMessenger):
        self.__bots_manager.messenger = messenger
