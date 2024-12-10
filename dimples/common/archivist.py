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
from typing import List, Optional

from dimsdk import DateTime
from dimsdk import SignKey, DecryptKey, VerifyKey, EncryptKey
from dimsdk import ID, Document, Meta
from dimsdk import UserDataSource, GroupDataSource
from dimsdk import Archivist

from ..utils import Logging

from .dbi import AccountDBI


# noinspection PyAbstractClass
class CommonArchivist(Archivist, UserDataSource, GroupDataSource, Logging, ABC):

    # each query will be expired after 10 minutes
    QUERY_EXPIRES = 600.0  # seconds

    def __init__(self, database: AccountDBI):
        super().__init__(expires=self.QUERY_EXPIRES)
        self.__db = database

    @property
    def database(self) -> AccountDBI:
        return self.__db

    # Override
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
            elif last_time is None or last_time.before(his_time):
                last_time = his_time
        return last_time

    async def local_users(self) -> List[ID]:
        db = self.database
        return await db.get_local_users()

    # Override
    async def save_meta(self, meta: Meta, identifier: ID) -> bool:
        db = self.database
        return await db.save_meta(meta=meta, identifier=identifier)

    # Override
    async def save_document(self, document: Document) -> bool:
        doc_time = document.time
        if doc_time is None:
            # assert False, 'document error: %s' % doc
            self.warning(msg='document without time: %s' % document.identifier)
        else:
            # calibrate the clock
            # make sure the document time is not in the far future
            current = DateTime.now() + 65.0
            if doc_time > current:
                # assert False, 'document time error: %s, %s' % (doc_time, document)
                return False
        db = self.database
        return await db.save_document(document=document)

    #
    #   EntityDataSource
    #

    # Override
    async def get_meta(self, identifier: ID) -> Optional[Meta]:
        db = self.database
        return await db.get_meta(identifier=identifier)

    # Override
    async def get_documents(self, identifier: ID) -> List[Document]:
        db = self.database
        return await db.get_documents(identifier=identifier)

    #
    #   UserDataSource
    #

    # Override
    async def get_contacts(self, identifier: ID) -> List[ID]:
        db = self.database
        return await db.get_contacts(user=identifier)

    # Override
    async def public_key_for_encryption(self, identifier: ID) -> Optional[EncryptKey]:
        raise AssertionError('DON\'T call me!')

    # Override
    async def public_keys_for_verification(self, identifier: ID) -> List[VerifyKey]:
        raise AssertionError('DON\'T call me!')

    # Override
    async def private_keys_for_decryption(self, identifier: ID) -> List[DecryptKey]:
        db = self.database
        return await db.private_keys_for_decryption(user=identifier)

    # Override
    async def private_key_for_signature(self, identifier: ID) -> Optional[SignKey]:
        db = self.database
        return await db.private_key_for_signature(user=identifier)

    # Override
    async def private_key_for_visa_signature(self, identifier: ID) -> Optional[SignKey]:
        db = self.database
        return await db.private_key_for_visa_signature(user=identifier)

    #
    #   GroupDataSource
    #

    # Override
    async def get_founder(self, identifier: ID) -> Optional[ID]:
        db = self.database
        return await db.get_founder(group=identifier)

    # Override
    async def get_owner(self, identifier: ID) -> Optional[ID]:
        db = self.database
        return await db.get_owner(group=identifier)

    # Override
    async def get_members(self, identifier: ID) -> List[ID]:
        db = self.database
        return await db.get_members(group=identifier)

    # Override
    async def get_assistants(self, identifier: ID) -> List[ID]:
        db = self.database
        return await db.get_assistants(group=identifier)

    #
    #   Organization Structure
    #

    async def get_administrators(self, group: ID) -> List[ID]:
        db = self.database
        return await db.get_administrators(group=group)

    async def save_administrators(self, administrators: List[ID], group: ID) -> bool:
        db = self.database
        return await db.save_administrators(administrators=administrators, group=group)

    async def save_members(self, members: List[ID], group: ID) -> bool:
        db = self.database
        return await db.save_members(members=members, group=group)
