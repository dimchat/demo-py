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
    Common extensions for Facebook
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    Barrack for cache entities
"""

from typing import Optional, List

from dimsdk import SignKey, DecryptKey
from dimsdk import ID, Meta, Document, User, Group
from dimsdk import Facebook

from .dbi import AccountDBI


class CommonFacebook(Facebook):

    def __init__(self):
        super().__init__()
        self.__database: Optional[AccountDBI] = None
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

    @database.setter
    def database(self, db: AccountDBI):
        self.__database = db

    #
    #   Super
    #

    @property  # Override
    def local_users(self) -> List[User]:
        db = self.database
        users = []
        array = db.local_users()
        # 'users.js' empty?
        if array is None or len(array) == 0:
            current = self.__current
            return [] if current is None else [current]
        # create users
        for item in array:
            usr = self.user(identifier=item)
            assert usr is not None, 'failed to create user: %s' % item
            # assert self.private_key_for_signature(identifier=item) is not None
            users.append(usr)
        return users

    @property  # Override
    def current_user(self) -> Optional[User]:
        """ Get current user (for signing and sending message) """
        current = self.__current
        if current is None:
            # current = super().current_user
            users = self.local_users
            if users is not None and len(users) > 0:
                current = users[0]
        return current

    @current_user.setter
    def current_user(self, user: User):
        self.__current = user

    # Override
    def save_meta(self, meta: Meta, identifier: ID) -> bool:
        db = self.database
        return db.save_meta(meta=meta, identifier=identifier)

    # Override
    def save_document(self, document: Document) -> bool:
        db = self.database
        return db.save_document(document=document)

    # Override
    def save_members(self, members: List[ID], identifier: ID) -> bool:
        db = self.database
        return db.save_members(members=members, identifier=identifier)

    def save_assistants(self, assistants: List[ID], identifier: ID) -> bool:
        db = self.database
        return db.save_assistants(assistants=assistants, identifier=identifier)

    # Override
    def create_user(self, identifier: ID) -> Optional[User]:
        if not identifier.is_broadcast:
            if self.public_key_for_encryption(identifier=identifier) is None:
                # visa.key not found
                return None
        return super().create_user(identifier=identifier)

    # Override
    def create_group(self, identifier: ID) -> Optional[Group]:
        if not identifier.is_broadcast:
            if self.meta(identifier=identifier) is None:
                # meta not found
                return None
        return super().create_group(identifier=identifier)

    #
    #   UserDataSource
    #

    # Override
    def contacts(self, identifier: ID) -> List[ID]:
        db = self.database
        return db.contacts(identifier=identifier)

    # Override
    def private_keys_for_decryption(self, identifier: ID) -> List[DecryptKey]:
        db = self.database
        return db.private_keys_for_decryption(identifier=identifier)

    # Override
    def private_key_for_signature(self, identifier: ID) -> Optional[SignKey]:
        db = self.database
        return db.private_key_for_signature(identifier=identifier)

    # Override
    def private_key_for_visa_signature(self, identifier: ID) -> Optional[SignKey]:
        db = self.database
        return db.private_key_for_visa_signature(identifier=identifier)

    #
    #    GroupDataSource
    #

    # Override
    def founder(self, identifier: ID) -> ID:
        db = self.database
        user = db.founder(identifier=identifier)
        if user is not None:
            # got from database
            return user
        return super().founder(identifier=identifier)

    # Override
    def owner(self, identifier: ID) -> ID:
        db = self.database
        user = db.owner(identifier=identifier)
        if user is not None:
            # got from database
            return user
        return super().owner(identifier=identifier)

    # Override
    def members(self, identifier: ID) -> Optional[List[ID]]:
        db = self.database
        users = db.members(identifier=identifier)
        if users is not None and len(users) > 0:
            # got from database
            return users
        return super().members(identifier=identifier)

    # Override
    def assistants(self, identifier: ID) -> Optional[List[ID]]:
        db = self.database
        bots = db.assistants(identifier=identifier)
        if bots is not None and len(bots) > 0:
            # got from database
            return bots
        return super().assistants(identifier=identifier)

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
    def document(self, identifier: ID, doc_type: str = '*') -> Optional[Document]:
        # if identifier.is_broadcast:
        #     # broadcast ID has no document
        #     return None
        db = self.database
        return db.document(identifier=identifier, doc_type=doc_type)
