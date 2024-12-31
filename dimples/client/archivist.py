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

from abc import ABC
from typing import Optional

from dimsdk import ID
from dimsdk import Group

from ..common import CommonArchivist

from ..group import SharedGroupManager


class ClientArchivist(CommonArchivist, ABC):

    # Override
    async def create_group(self, identifier: ID) -> Optional[Group]:
        group = await super().create_group(identifier=identifier)
        if group is not None:
            delegate = group.data_source
            if delegate is None or delegate is self.facebook:
                # replace group's data source
                group.data_source = SharedGroupManager()
        return group

    #
    # # each respond will be expired after 10 minutes
    # RESPOND_EXPIRES = 600.0  # seconds
    #
    # def __init__(self,, facebook: Facebook, database: AccountDBI):
    #     super().__init__(facebook=facebook, database=database)
    #     self.__document_responses = FrequencyChecker(expires=self.RESPOND_EXPIRES)
    #     self.__last_active_members: Dict[ID, ID] = {}  # group => member
    #     # twins
    #     self.__facebook = None
    #     self.__messenger = None
    #
    # @property
    # def facebook(self) -> Optional[CommonFacebook]:
    #     ref = self.__facebook
    #     if ref is not None:
    #         return ref()
    #
    # @property
    # def messenger(self) -> Optional[CommonMessenger]:
    #     ref = self.__messenger
    #     if ref is not None:
    #         return ref()
    #
    # @facebook.setter
    # def facebook(self, barrack: CommonFacebook):
    #     self.__facebook = weakref.ref(barrack)
    #
    # @messenger.setter
    # def messenger(self, transceiver: CommonMessenger):
    #     self.__messenger = weakref.ref(transceiver)
    #
    # # protected
    # def is_documents_respond_expired(self, identifier: ID, force: bool) -> bool:
    #     return self.__document_responses.is_expired(key=identifier, force=force)
    #
    # def set_last_active_member(self, member: ID, group: ID):
    #     self.__last_active_members[group] = member
    #
    # # Override
    # async def check_meta(self, identifier: ID, meta: Optional[Meta]) -> bool:
    #     if identifier.is_broadcast:
    #         # broadcast entity has no meta to query
    #         return False
    #     else:
    #         return await super().check_meta(identifier=identifier, meta=meta)
    #
    # # Override
    # async def check_documents(self, identifier: ID, documents: List[Document]) -> bool:
    #     if identifier.is_broadcast:
    #         # broadcast entity has no document to update
    #         return False
    #     else:
    #         return await super().check_documents(identifier=identifier, documents=documents)
    #
    # # Override
    # async def check_members(self, group: ID, members: List[ID]) -> bool:
    #     if group.is_broadcast:
    #         # broadcast entity has no members to update
    #         return False
    #     else:
    #         return await super().check_members(group=group, members=members)
    #
    # def _check_session_ready(self) -> bool:
    #     messenger = self.messenger
    #     if messenger is None:
    #         return False
    #     session = messenger.session
    #     return isinstance(session, ClientSession) and session.ready

