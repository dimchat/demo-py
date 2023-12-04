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

from typing import Optional, List

from dimsdk import SignKey, DecryptKey
from dimsdk import ID, User
from dimsdk import Meta
from dimsdk import Document, DocumentHelper
from dimsdk import Facebook

from ..utils import Logging

from .dbi import AccountDBI

from .anonymous import Anonymous


class CommonFacebook(Facebook, Logging):

    def __init__(self, database: AccountDBI):
        super().__init__()
        self.__database = database
        self.__current: Optional[User] = None

    @property
    def database(self) -> AccountDBI:
        """
            Database
            ~~~~~~~~
            PrivateKeys, Metas, Documents,
            Users, Contacts, Groups, Members
        """
        return self.__database

    #
    #   Super
    #

    @property  # Override
    def local_users(self) -> List[User]:
        current = self.__current
        return [] if current is None else [current]

    @property
    def current_user(self) -> Optional[User]:
        """ Get current user (for signing and sending message) """
        return self.__current

    @current_user.setter
    def current_user(self, user: User):
        if user.data_source is None:
            user.data_source = self
        self.__current = user

    def document(self, identifier: ID, doc_type: str = '*') -> Optional[Document]:
        all_documents = self.documents(identifier=identifier)
        doc = DocumentHelper.last_document(all_documents, doc_type)
        # compatible for document type
        if doc is None and doc_type == Document.VISA:
            doc = DocumentHelper.last_document(all_documents, 'profile')
        return doc

    def get_name(self, identifier: ID) -> str:
        if identifier.is_user:
            doc_type = Document.VISA
        elif identifier.is_group:
            doc_type = Document.BULLETIN
        else:
            doc_type = '*'
        # get name from document
        doc = self.document(identifier=identifier, doc_type=doc_type)
        if doc is not None:
            name = doc.name
            if name is not None and len(name) > 0:
                return name
        # get name from ID
        return Anonymous.get_name(identifier=identifier)

    # Override
    def save_meta(self, meta: Meta, identifier: ID) -> bool:
        # check valid
        if meta.valid and meta.match_identifier(identifier=identifier):
            pass
        else:
            # assert False, 'meta not valid: %s' % identifier
            return False
        # check old meta
        old = self.meta(identifier=identifier)
        if old is not None:
            # assert meta == old, 'meta should not changed'
            return True
        # meta not exists yet, save it
        db = self.database
        return db.save_meta(meta=meta, identifier=identifier)

    # Override
    def save_document(self, document: Document) -> bool:
        identifier = document.identifier
        if not document.valid:
            # try to verify
            meta = self.meta(identifier=identifier)
            if meta is None:
                self.error(msg='meta not found: %s' % identifier)
                return False
            elif document.verify(public_key=meta.public_key):
                self.debug(msg='document verified: %s' % identifier)
            else:
                self.error(msg='failed to verify document: %s' % identifier)
                # assert False, 'document not valid: %s' % identifier
                return False
        doc_type = document.type
        if doc_type is None:
            doc_type = '*'
        # check old documents with type
        documents = self.documents(identifier=identifier)
        old = DocumentHelper.last_document(documents, doc_type)
        if old is not None and DocumentHelper.is_expired(document, old):
            self.warning(msg='drop expired document: %s' % identifier)
            return False
        db = self.database
        return db.save_document(document=document)

    #
    #   EntityDataSource
    #

    # Override
    def meta(self, identifier: ID) -> Optional[Meta]:
        # if identifier.is_broadcast:
        #     # broadcast ID has no meta
        #     return None
        db = self.database
        return db.meta(identifier=identifier)

    # Override
    def documents(self, identifier: ID) -> List[Document]:
        # if identifier.is_broadcast:
        #     # broadcast ID has no documents
        #     return None
        db = self.database
        return db.documents(identifier=identifier)

    #
    #   UserDataSource
    #

    # Override
    def contacts(self, identifier: ID) -> List[ID]:
        db = self.database
        return db.contacts(user=identifier)

    # Override
    def private_keys_for_decryption(self, identifier: ID) -> List[DecryptKey]:
        db = self.database
        return db.private_keys_for_decryption(user=identifier)

    # Override
    def private_key_for_signature(self, identifier: ID) -> Optional[SignKey]:
        db = self.database
        return db.private_key_for_signature(user=identifier)

    # Override
    def private_key_for_visa_signature(self, identifier: ID) -> Optional[SignKey]:
        db = self.database
        return db.private_key_for_visa_signature(user=identifier)

    #
    #    GroupDataSource
    #

    # Override
    def founder(self, identifier: ID) -> Optional[ID]:
        db = self.database
        user = db.founder(group=identifier)
        if user is None:
            user = super().founder(identifier=identifier)
        return user

    # Override
    def owner(self, identifier: ID) -> Optional[ID]:
        db = self.database
        user = db.owner(group=identifier)
        if user is None:
            user = super().owner(identifier=identifier)
        return user

    # Override
    def members(self, identifier: ID) -> List[ID]:
        owner = self.owner(identifier=identifier)
        if owner is None:
            # assert False, 'group owner not found: %s' % identifier
            return []
        db = self.database
        users = db.members(group=identifier)
        if len(users) == 0:
            users = super().members(identifier=identifier)
            if len(users) == 0:
                users = [owner]
        assert owner == users[0], 'group owner must be the first member: %s, group: %s' % (owner, identifier)
        return users

    # Override
    def assistants(self, identifier: ID) -> List[ID]:
        db = self.database
        bots = db.assistants(group=identifier)
        if len(bots) == 0:
            bots = super().assistants(identifier=identifier)
        return bots
