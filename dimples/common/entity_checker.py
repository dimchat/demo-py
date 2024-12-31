# -*- coding: utf-8 -*-
#
#   DIM-SDK : Decentralized Instant Messaging Software Development Kit
#
#                                Written in 2024 by Moky <albert.moky@gmail.com>
#
# ==============================================================================
# MIT License
#
# Copyright (c) 2024 Albert Moky
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

from dimsdk import DateTime
from dimsdk import ID, Meta, Document, Visa

from ..utils import FrequencyChecker, RecentTimeChecker

from .dbi import AccountDBI


class EntityChecker(ABC):

    # each query will be expired after 10 minutes
    QUERY_EXPIRES = 10 * 60

    # each respond will be expired after 10 minutes
    RESPOND_EXPIRES = 10 * 60

    def __init__(self, database: AccountDBI):
        super().__init__()
        self.__database = database
        # query checkers
        self.__meta_queries = FrequencyChecker(expires=self.QUERY_EXPIRES)
        self.__docs_queries = FrequencyChecker(expires=self.QUERY_EXPIRES)
        self.__members_queries = FrequencyChecker(expires=self.QUERY_EXPIRES)
        # response checker
        self.__visa_responses = FrequencyChecker(expires=self.QUERY_EXPIRES)
        # recent time checkers
        self.__last_document_times = RecentTimeChecker()
        self.__last_history_times = RecentTimeChecker()
        # group => member
        self.__last_active_members: Dict[ID, ID] = {}

    @property
    def database(self) -> AccountDBI:
        return self.__database

    # protected
    def is_meta_query_expired(self, identifier: ID) -> bool:
        return self.__meta_queries.is_expired(key=identifier)

    # protected
    def is_document_query_expired(self, identifier: ID) -> bool:
        return self.__docs_queries.is_expired(key=identifier)

    # protected
    def is_members_query_expired(self, identifier: ID) -> bool:
        return self.__members_queries.is_expired(key=identifier)

    # protected
    def is_document_response_expired(self, identifier: ID, force: bool) -> bool:
        return self.__visa_responses.is_expired(key=identifier, force=force)

    def set_last_active_member(self, member: ID, group: ID):
        """ Set last active member for group """
        self.__last_active_members[group] = member

    # protected
    def get_last_active_member(self, group: ID) -> Optional[ID]:
        return self.__last_active_members.get(group)

    def set_last_document_time(self, now: DateTime, identifier: ID):
        """ Update 'SDT' - Sender Document Time """
        self.__last_document_times.set_last_time(key=identifier, now=now)

    def set_last_group_history_time(self, now: DateTime, identifier: ID):
        """ Update 'GHT' - Group History Time """
        self.__last_history_times.set_last_time(key=identifier, now=now)

    #
    #   Meta
    #

    async def check_meta(self, identifier: ID, meta: Optional[Meta]) -> bool:
        """
        Check meta for querying

        :param identifier: entity ID
        :param meta:       exists meta
        :return: True on querying
        """
        if self.needs_query_meta(identifier=identifier, meta=meta):
            # if not self.is_meta_query_expired(identifier=identifier):
            #     # query not expired yet
            #     return False
            return await self.query_meta(identifier=identifier)
        else:
            # no need to query meta again
            return False

    # protected
    # noinspection PyMethodMayBeStatic
    def needs_query_meta(self, identifier: ID, meta: Optional[Meta]) -> bool:
        """ check whether need to query meta """
        if identifier.is_broadcast:
            # broadcast entity has no meta to query
            return False
        elif meta is None:
            # meta not found, sure to query
            return True
        # assert MetaUtils.match_identifier(identifier, meta), 'meta not match: %s, %s' % (identifier, meta)
        return False

    #
    #   Documents
    #

    async def check_documents(self, identifier: ID, documents: List[Document]) -> bool:
        """
        Check documents for querying/updating

        :param identifier: entity ID
        :param documents:  exist document
        :return: True on querying
        """
        if self.needs_query_documents(identifier=identifier, documents=documents):
            # if not self.is_document_query_expired(identifier=identifier):
            #     # query not expired yet
            #     return False
            return await self.query_documents(identifier=identifier, documents=documents)
        else:
            # no need to update documents now
            return False

    def needs_query_documents(self, identifier: ID, documents: List[Document]) -> bool:
        """ check whether need to query documents """
        if identifier.is_broadcast:
            # broadcast entity has no document to query
            return False
        elif documents is None or len(documents) == 0:
            # documents not found, sure to query
            return True
        current = self.get_last_document_time(identifier=identifier, documents=documents)
        return self.__last_document_times.is_expired(key=identifier, now=current)

    # noinspection PyMethodMayBeStatic
    def get_last_document_time(self, identifier: ID, documents: List[Document]):
        if documents is None or len(documents) == 0:
            return None
        last_time = None
        for doc in documents:
            assert doc.identifier == identifier, 'document not match: %s, %s' % (identifier, doc)
            doc_time = doc.time
            if doc_time is None:
                # assert False, 'document error: %s' % doc
                continue
            elif last_time is None or last_time < doc_time:
                last_time = doc_time
        # OK
        return last_time

    #
    #   Group Members
    #

    async def check_members(self, group: ID, members: List[ID]) -> bool:
        """
        Check group members for querying

        :param group:   group ID
        :param members: exist members
        :return: True on querying
        """
        if await self.needs_query_members(group=group, members=members):
            # if not self.is_members_query_expired(group):
            #     # query not expired yet
            #     return False
            return await self.query_members(group=group, members=members)
        else:
            # no need to update group members now
            return False

    async def needs_query_members(self, group: ID, members: List[ID]) -> bool:
        """ check whether need to query group members """
        if group.is_broadcast:
            # broadcast group has no members to query
            return False
        elif members is None or len(members) == 0:
            # members not found, sure to query
            return True
        current = await self.get_last_group_history_time(group=group)
        return self.__last_history_times.is_expired(key=group, now=current)

    async def get_last_group_history_time(self, group: ID) -> Optional[DateTime]:
        db = self.database
        array = await db.get_group_histories(group=group)
        if array is None or len(array) == 0:
            return None
        last_time: Optional[DateTime] = None
        for cmd, _ in array:
            his_time = cmd.time
            if his_time is None:
                assert False, 'group command error: %s' % cmd
                pass
            elif last_time is None or last_time < his_time:
                last_time = his_time
        # OK
        return last_time

    #
    #   Querying
    #

    async def query_meta(self, identifier: ID) -> bool:
        """
        Request for meta with entity ID
            (call 'isMetaQueryExpired()' before sending command)

        :param identifier: entity ID
        :return: False on duplicated
        """
        raise NotImplemented

    async def query_documents(self, identifier: ID, documents: List[Document]) -> bool:
        """
        Request for documents with entity ID
            (call 'isDocumentQueryExpired()' before sending command)

        :param identifier: entity ID
        :param documents:  exist documents
        :return: False on duplicated
        """
        raise NotImplemented

    async def query_members(self, group: ID, members: List[ID]) -> bool:
        """
        Request for group members with group ID
            (call 'isMembersQueryExpired()' before sending command)

        :param group:   group ID
        :param members: exist members
        :return: False on duplicated
        """
        raise NotImplemented

    #
    #   Responding
    #

    async def send_visa(self, visa: Visa, receiver: ID, updated: bool = False) -> bool:
        """
        Send my visa document to contact
            if document is updated, force to send it again.
            else only send once every 10 minutes.

        :param visa:
        :param receiver:
        :param updated:
        :return: False on error
        """
        raise NotImplemented
