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
from dimsdk import VerifyKey, EncryptKey
from dimsdk import SignKey, DecryptKey
from dimsdk import ID, User
from dimsdk import Meta, Document, Visa, Bulletin
from dimsdk import Facebook
from dimsdk import MetaUtils, DocumentUtils
from dimsdk import DocumentType

from ..utils import Logging
from ..utils import Runner

from .dbi import AccountDBI

from .ans import AddressNameServer
from .checker import EntityChecker
from .archivist import CommonArchivist
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
    def barrack(self) -> CommonArchivist:
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
        if user is None:
            all_users = await self.barrack.local_users
            if len(all_users) > 0:
                user = all_users[0]
                self.__current = user
        return user

    async def set_current_user(self, user: User):
        if user.data_source is None:
            user.data_source = self
        self.__current = user

    # Override
    async def select_user(self, receiver: ID) -> Optional[User]:
        local_users = await self.barrack.local_users
        user = self.__current
        if user is not None:  # and user not in local_users:
            local_users.insert(0, user)
        #
        #  1.
        #
        if len(local_users) == 0:
            self.error(msg='local users should not be empty')
            return None
        elif receiver.is_broadcast:
            # broadcast message can decrypt by anyone, so
            # just return current user
            return local_users[0]
        #
        #  2.
        #
        if receiver.is_user:
            # personal message
            for item in local_users:
                if item.identifier == receiver:
                    # DISCUSS: set this item to be current user?
                    return item
        else:
            # group message(recipient not designated)
            assert receiver.is_group, 'receiver error: %s' % receiver
            # the messenger will check group info before decrypting message,
            # so we can trust that the group's meta & members MUST exist here.
            members = await self.get_members(identifier=receiver)
            # assert len(members) > 0, 'members not found: %s' % receiver
            for item in local_users:
                if item.identifier in members:
                    # DISCUSS: set this item to be current user?
                    return item
        # not me?
        return None

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
        doc_type = DocumentUtils.get_document_type(document=document)
        if doc_type is None:
            doc_type = '*'
        # check old documents with type
        docs = await self.get_documents(identifier=identifier)
        old = DocumentUtils.last_document(documents=docs, doc_type=doc_type)
        return old is not None and DocumentUtils.is_expired(document, old)

    # Override
    async def get_meta_key(self, identifier: ID) -> Optional[VerifyKey]:
        meta = await self.get_meta(identifier=identifier)
        if meta is not None:  # and meta.valid:
            return meta.public_key

    # Override
    async def get_visa_key(self, identifier: ID) -> Optional[EncryptKey]:
        docs = await self.get_documents(identifier=identifier)
        if docs is not None:
            visa = DocumentUtils.last_visa(documents=docs)
            if visa is not None:  # and visa.valid:
                return visa.public_key

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
