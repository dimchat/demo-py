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

from dimsdk import DateTime
from dimsdk import SignKey, DecryptKey
from dimsdk import ID, User
from dimsdk import Meta, Document, Visa, Bulletin
from dimsdk import Facebook
from dimsdk import MetaUtils, DocumentUtils

from ..utils import Logging
from ..utils import Runner

from .dbi import AccountDBI

from .entity_checker import EntityChecker
from .archivist import CommonArchivist
from .anonymous import Anonymous


class CommonFacebook(Facebook, Logging, ABC):

    def __init__(self, database: AccountDBI):
        super().__init__()
        self.__database = database
        self.__archivist: Optional[CommonArchivist] = None
        self.__current: Optional[User] = None

    @property
    def database(self) -> AccountDBI:
        return self.__database

    @property  # Override
    def archivist(self) -> CommonArchivist:
        return self.__archivist

    @archivist.setter
    def archivist(self, delegate: CommonArchivist):
        self.__archivist = delegate

    @property
    @abstractmethod
    def checker(self) -> Optional[EntityChecker]:
        raise NotImplemented

    #
    #   Current User
    #

    @property
    async def current_user(self) -> Optional[User]:
        """ Get current user (for signing and sending message) """
        user = self.__current
        if user is None:
            all_users = await self.archivist.local_users
            if len(all_users) > 0:
                user = all_users[0]
                self.__current = user
        return user

    async def set_current_user(self, user: User):
        if user.data_source is None:
            user.data_source = self
        self.__current = user

    #
    #   Documents
    #

    async def get_document(self, identifier: ID, doc_type: str = '*') -> Optional[Document]:
        all_documents = await self.get_documents(identifier=identifier)
        doc = DocumentUtils.last_document(all_documents, doc_type)
        # compatible for document type
        if doc is None and doc_type == Document.VISA:
            doc = DocumentUtils.last_document(all_documents, Document.PROFILE)
        return doc

    async def get_visa(self, user: ID) -> Optional[Visa]:
        docs = await self.get_documents(identifier=user)
        return DocumentUtils.last_visa(documents=docs)

    async def get_bulletin(self, group: ID) -> Optional[Bulletin]:
        docs = await self.get_documents(identifier=group)
        return DocumentUtils.last_bulletin(documents=docs)

    async def get_name(self, identifier: ID) -> str:
        if identifier.is_user:
            doc_type = Document.VISA
        elif identifier.is_group:
            doc_type = Document.BULLETIN
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
    #   Storage
    #

    # Override
    async def save_meta(self, meta: Meta, identifier: ID) -> bool:
        #
        #  1. check valid
        #
        if not self._check_meta(meta=meta, identifier=identifier):
            # assert False, 'meta not valid: %s' % identifier
            return False
        #
        #  2. check duplicated
        #
        old = await self.get_meta(identifier=identifier)
        if old is not None:
            self.debug(msg='meta duplicated: %s' % identifier)
            return True
        #
        #  3. save into database
        #
        db = self.database
        return await db.save_meta(meta=meta, identifier=identifier)

    # noinspection PyMethodMayBeStatic
    def _check_meta(self, meta: Meta, identifier: ID) -> bool:
        return meta.valid and MetaUtils.match_identifier(identifier=identifier, meta=meta)

    # Override
    async def save_document(self, document: Document) -> bool:
        #
        #  1. check valid
        #
        if await self._check_document_valid(document=document):
            # document valid
            pass
        else:
            # assert False, 'meta not valid: %s' % document.identifier
            return False
        #
        #  2. check expired
        #
        if await self._check_document_expired(document=document):
            self.info(msg='drop expired document: %s' % document)
            return False
        #
        #  3. save into database
        #
        db = self.database
        return await db.save_document(document=document)

    async def _check_document_valid(self, document: Document) -> bool:
        identifier = document.identifier
        doc_time = document.time
        # check document time
        if doc_time is None:
            self.warning(msg='document without time: %s' % identifier)
        else:
            # calibrate the clock
            # make sure the document time is not in the far future
            near_future = DateTime.now() + 30 * 60
            if doc_time > near_future:
                self.error(msg='document time error: %s, %s' % (doc_time, identifier))
                return False
        # check valid
        return await self._verify_document(document=document)

    async def _verify_document(self, document: Document) -> bool:
        if document.valid:
            return True
        identifier = document.identifier
        meta = await self.get_meta(identifier=identifier)
        if meta is None:
            self.warning(msg='failed to get meta: %s' % identifier)
            return False
        return document.verify(public_key=meta.public_key)

    async def _check_document_expired(self, document: Document) -> bool:
        identifier = document.identifier
        doc_type = document.type
        if doc_type is None:
            doc_type = '*'
        # check old documents with type
        docs = await self.get_documents(identifier=identifier)
        old = DocumentUtils.last_document(documents=docs, doc_type=doc_type)
        return old is not None and DocumentUtils.is_expired(document, old)

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
