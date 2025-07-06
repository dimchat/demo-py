# -*- coding: utf-8 -*-
#
#   DIM-SDK : Decentralized Instant Messaging Software Development Kit
#
#                                Written in 2022 by Moky <albert.moky@gmail.com>
#
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
    Common extensions for Facebook
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    Barrack for cache entities
"""

from abc import ABC, abstractmethod
from typing import Optional, List

from dimsdk import SignKey, DecryptKey
from dimsdk import ID, User
from dimsdk import Meta, Document, Visa, Bulletin
from dimsdk import Facebook
from dimsdk import DocumentUtils
from dimsdk import DocumentType

from ..utils import Logging
from ..utils import Runner

from .dbi import AccountDBI

from .ans import AddressNameServer
from .checker import EntityChecker
from .archivist import Archivist, CommonArchivist
from .anonymous import Anonymous


class CommonFacebook(Facebook, Logging, ABC):

    def __init__(self, database: AccountDBI):
        super().__init__()
        self.__database = database
        self.__barrack: Optional[CommonArchivist] = None
        self.__checker: Optional[EntityChecker] = None
        self.__current: Optional[User] = None

    @property
    def database(self) -> AccountDBI:
        return self.__database

    @property  # Override
    def archivist(self) -> Optional[Archivist]:
        return self.__barrack

    @property  # Override
    def barrack(self) -> Optional[CommonArchivist]:
        return self.__barrack

    @barrack.setter
    def barrack(self, archivist: CommonArchivist):
        self.__barrack = archivist

    @property
    def checker(self) -> Optional[EntityChecker]:
        return self.__checker

    @checker.setter
    def checker(self, ec: EntityChecker):
        self.__checker = ec

    #
    #   Current User
    #

    @property
    async def current_user(self) -> Optional[User]:
        """ Get current user (for signing and sending message) """
        user = self.__current
        if user is not None:
            return user
        array = await self.database.get_local_users()
        if array is None or len(array) == 0:
            return None
        else:
            me = array[0]
        assert await self.private_key_for_signature(identifier=me), 'user error: %s' % me
        user = await self.get_user(identifier=me)
        self.__current = user
        return user

    async def set_current_user(self, user: User):
        if user.data_source is None:
            user.data_source = self
        self.__current = user

    # Override
    async def select_local_user(self, receiver: ID) -> Optional[ID]:
        user = self.__current
        if user is not None:
            me = user.identifier
            if receiver.is_broadcast:
                # broadcast message can be decrypted by anyone, so
                # just return current user here
                return me
            elif receiver.is_group:
                # group message (recipient not designated)
                #
                # the messenger will check group info before decrypting message,
                # so we can trust that the group's meta & members MUST exist here.
                members = await self.get_members(identifier=receiver)
                if members is None or len(members) == 0:
                    self.warning(msg='members not found: %s' % receiver)
                    return None
                elif me in members:
                    return me
            elif receiver == me:
                return me
        # check local users
        return await super().select_local_user(receiver=receiver)

    #
    #   Documents
    #

    async def get_document(self, identifier: ID, doc_type: str = '*') -> Optional[Document]:
        all_documents = await self.get_documents(identifier=identifier)
        doc = DocumentUtils.last_document(all_documents, doc_type)
        # compatible for document type
        if doc is None and doc_type == DocumentType.VISA:
            doc = DocumentUtils.last_document(all_documents, DocumentType.PROFILE)
        return doc

    async def get_visa(self, user: ID) -> Optional[Visa]:
        docs = await self.get_documents(identifier=user)
        return DocumentUtils.last_visa(documents=docs)

    async def get_bulletin(self, group: ID) -> Optional[Bulletin]:
        docs = await self.get_documents(identifier=group)
        return DocumentUtils.last_bulletin(documents=docs)

    async def get_name(self, identifier: ID) -> str:
        if identifier.is_user:
            doc_type = DocumentType.VISA
        elif identifier.is_group:
            doc_type = DocumentType.BULLETIN
        else:
            doc_type = '*'
        # get name from document
        doc = await self.get_document(identifier=identifier, doc_type=doc_type)
        if doc is not None:
            name = doc.name
            if name is not None and len(name) > 0:
                return name
        # get name from ID
        return Anonymous.get_name(identifier=identifier)

    #
    #   Entity DataSource
    #

    # Override
    async def get_meta(self, identifier: ID) -> Optional[Meta]:
        db = self.database
        meta = await db.get_meta(identifier=identifier)
        checker = self.checker
        if checker is not None:
            coro = checker.check_meta(identifier=identifier, meta=meta)
            Runner.async_task(coro=coro)
        return meta

    # Override
    async def get_documents(self, identifier: ID) -> List[Document]:
        db = self.database
        docs = await db.get_documents(identifier=identifier)
        checker = self.checker
        if checker is not None:
            coro = checker.check_documents(identifier=identifier, documents=docs)
            Runner.async_task(coro=coro)
        return docs

    #
    #   User DataSource
    #

    # Override
    async def get_contacts(self, identifier: ID) -> List[ID]:
        db = self.database
        return await db.get_contacts(identifier)

    # Override
    async def private_keys_for_decryption(self, identifier: ID) -> List[DecryptKey]:
        db = self.database
        return await db.private_keys_for_decryption(identifier)

    # Override
    async def private_key_for_signature(self, identifier: ID) -> Optional[SignKey]:
        db = self.database
        return await db.private_key_for_signature(identifier)

    # Override
    async def private_key_for_visa_signature(self, identifier: ID) -> Optional[SignKey]:
        db = self.database
        return await db.private_key_for_visa_signature(identifier)

    #
    #    Organizational Structure
    #

    @abstractmethod
    async def get_administrators(self, group: ID) -> List[ID]:
        raise NotImplemented

    @abstractmethod
    async def save_administrators(self, administrators: List[ID], group: ID) -> bool:
        raise NotImplemented

    @abstractmethod
    async def save_members(self, members: List[ID], group: ID) -> bool:
        raise NotImplemented

    #
    #   Address Name Service
    #
    ans: Optional[AddressNameServer] = None
