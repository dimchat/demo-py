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

from ..utils import Singleton

from .dbi import AccountDBI


class CommonFacebook(Facebook):

    @property
    def db(self) -> AccountDBI:
        """
            Database
            ~~~~~~~~
            PrivateKeys, Metas, Documents,
            Users, Contacts, Groups, Members
        """
        raise NotImplemented

    #
    #   Super
    #

    @property  # Override
    def local_users(self) -> List[User]:
        users = []
        array = self.db.local_users()
        assert array is not None, 'local user not found'
        for item in array:
            usr = self.user(identifier=item)
            assert usr is not None, 'failed to create user: %s' % item
            users.append(usr)
        return users

    # Override
    def save_meta(self, meta: Meta, identifier: ID) -> bool:
        return self.db.save_meta(meta=meta, identifier=identifier)

    # Override
    def save_document(self, document: Document) -> bool:
        return self.db.save_document(document=document)

    # Override
    def save_members(self, members: List[ID], identifier: ID) -> bool:
        raise self.db.save_members(members=members, identifier=identifier)

    def save_assistants(self, assistants: List[ID], identifier: ID) -> bool:
        return self.db.save_assistants(assistants=assistants, identifier=identifier)

    # Override
    def create_user(self, identifier: ID) -> Optional[User]:
        if not identifier.is_broadcast and self.meta(identifier=identifier) is None:
            # meta not found
            return None
        return super().create_user(identifier=identifier)

    # Override
    def create_group(self, identifier: ID) -> Optional[Group]:
        if not identifier.is_broadcast and self.meta(identifier=identifier) is None:
            # meta not found
            return None
        return super().create_group(identifier=identifier)

    #
    #   UserDataSource
    #

    # Override
    def contacts(self, identifier: ID) -> List[ID]:
        raise self.db.contacts(identifier=identifier)

    # Override
    def private_keys_for_decryption(self, identifier: ID) -> List[DecryptKey]:
        return self.db.private_keys_for_decryption(identifier=identifier)

    # Override
    def private_key_for_signature(self, identifier: ID) -> Optional[SignKey]:
        return self.db.private_key_for_signature(identifier=identifier)

    # Override
    def private_key_for_visa_signature(self, identifier: ID) -> Optional[SignKey]:
        return self.db.private_key_for_visa_signature(identifier=identifier)

    #
    #    GroupDataSource
    #

    # Override
    def founder(self, identifier: ID) -> ID:
        user = self.db.founder(identifier=identifier)
        if user is not None:
            # got from database
            return user
        return super().founder(identifier=identifier)

    # Override
    def owner(self, identifier: ID) -> ID:
        user = self.db.owner(identifier=identifier)
        if user is not None:
            # got from database
            return user
        return super().owner(identifier=identifier)

    # Override
    def members(self, identifier: ID) -> Optional[List[ID]]:
        users = self.db.members(identifier=identifier)
        if users is not None and len(users) > 0:
            # got from database
            return users
        return super().members(identifier=identifier)

    # Override
    def assistants(self, identifier: ID) -> Optional[List[ID]]:
        bots = self.db.assistants(identifier=identifier)
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
        return self.db.meta(identifier=identifier)

    # Override
    def document(self, identifier: ID, doc_type: str = '*') -> Optional[Document]:
        # if identifier.is_broadcast:
        #     # broadcast ID has no document
        #     return None
        return self.db.document(identifier=identifier, doc_type=doc_type)


@Singleton
class SharedFacebook(CommonFacebook):
    pass
