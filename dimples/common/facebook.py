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
from dimsdk import Document, DocumentHelper
from dimsdk import Facebook

from ..utils import Logging

from .archivist import CommonArchivist
from .anonymous import Anonymous


class CommonFacebook(Facebook, Logging, ABC):

    def __init__(self):
        super().__init__()
        self.__current: Optional[User] = None

    @property  # Override
    @abstractmethod
    def archivist(self) -> CommonArchivist:
        raise NotImplemented

    #
    #   Super
    #

    @property  # Override
    async def local_users(self) -> List[User]:
        all_users = []
        # load from database
        array = await self.archivist.local_users()
        if array is None or len(array) == 0:
            # get current user
            user = self.__current
            if user is not None:
                all_users.append(user)
        else:
            for item in array:
                # assert self.private_key_for_signature(identifier=item) is not None, 'error: %s' % item
                user = await self.get_user(identifier=item)
                if user is not None:
                    all_users.append(user)
                # else:
                #     assert False, 'failed to create user: %s' % item
        # OK
        return all_users

    @property
    async def current_user(self) -> Optional[User]:
        """ Get current user (for signing and sending message) """
        user = self.__current
        if user is None:
            all_users = await self.local_users
            if len(all_users) > 0:
                user = all_users[0]
                self.__current = user
        return user

    async def set_current_user(self, user: User):
        if user.data_source is None:
            user.data_source = self
        self.__current = user

    async def get_document(self, identifier: ID, doc_type: str = '*') -> Optional[Document]:
        all_documents = await self.get_documents(identifier=identifier)
        doc = DocumentHelper.last_document(all_documents, doc_type)
        # compatible for document type
        if doc is None and doc_type == Document.VISA:
            doc = DocumentHelper.last_document(all_documents, Document.PROFILE)
        return doc

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
    #   UserDataSource
    #

    # Override
    async def get_contacts(self, identifier: ID) -> List[ID]:
        db = self.archivist
        return await db.get_contacts(identifier)

    # Override
    async def private_keys_for_decryption(self, identifier: ID) -> List[DecryptKey]:
        db = self.archivist
        return await db.private_keys_for_decryption(identifier)

    # Override
    async def private_key_for_signature(self, identifier: ID) -> Optional[SignKey]:
        db = self.archivist
        return await db.private_key_for_signature(identifier)

    # Override
    async def private_key_for_visa_signature(self, identifier: ID) -> Optional[SignKey]:
        db = self.archivist
        return await db.private_key_for_visa_signature(identifier)

    #
    #    Group
    #

    async def save_members(self, members: List[ID], group: ID) -> bool:
        db = self.archivist
        return await db.save_members(members=members, group=group)

    async def save_administrators(self, administrators: List[ID], group: ID) -> bool:
        db = self.archivist
        return await db.save_administrators(administrators=administrators, group=group)

    async def get_administrators(self, group: ID) -> List[ID]:
        db = self.archivist
        return await db.get_administrators(group=group)
