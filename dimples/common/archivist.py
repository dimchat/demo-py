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

import weakref
from typing import Optional, List

from dimsdk import DateTime
from dimsdk import VerifyKey, EncryptKey
from dimsdk import ID, Meta, Document
from dimsdk import MetaUtils, DocumentUtils
from dimsdk import User, Group
from dimsdk import Facebook
from dimsdk import Archivist
from dimsdk import Barrack

from ..utils import Logging
from ..utils import MemoryCache, ThanosCache

from .dbi import AccountDBI


class CommonArchivist(Barrack, Archivist, Logging):

    def __init__(self, facebook: Facebook, database: AccountDBI):
        super().__init__()
        self.__facebook = weakref.ref(facebook)
        self.__database = database
        # memory caches
        self.__user_cache = self._create_user_cache()
        self.__group_cache = self._create_group_cache()

    @property
    def facebook(self) -> Optional[Facebook]:
        return self.__facebook()

    @property
    def database(self) -> AccountDBI:
        return self.__database

    # noinspection PyMethodMayBeStatic
    def _create_user_cache(self) -> MemoryCache[ID, User]:
        return ThanosCache()

    # noinspection PyMethodMayBeStatic
    def _create_group_cache(self) -> MemoryCache[ID, Group]:
        return ThanosCache()

    def reduce_memory(self):
        """
        Call it when received 'UIApplicationDidReceiveMemoryWarningNotification',
        this will remove 50% of cached objects

        :return: number of survivors
        """
        cnt1 = self.__user_cache.reduce_memory()
        cnt2 = self.__group_cache.reduce_memory()
        return cnt1 + cnt2

    #
    #   Barrack
    #

    # Override
    def cache_user(self, user: User):
        if user.data_source is None:
            user.data_source = self.facebook
        self.__user_cache.put(key=user.identifier, value=user)

    # Override
    def cache_group(self, group: Group):
        if group.data_source is None:
            group.data_source = self.facebook
        self.__group_cache.put(key=group.identifier, value=group)

    # Override
    def get_user(self, identifier: ID):
        return self.__user_cache.get(key=identifier)

    # Override
    def get_group(self, identifier: ID):
        return self.__group_cache.get(key=identifier)

    #
    #   Archivist
    #

    # Override
    async def save_meta(self, meta: Meta, identifier: ID) -> bool:
        #
        #  1. check valid
        #
        if not self.check_meta(meta=meta, identifier=identifier):
            self.warning(msg='meta not valid: %s' % identifier)
            return False
        #
        #  2. check duplicated
        #
        old = await self.facebook.get_meta(identifier=identifier)
        if old is not None:
            self.debug(msg='meta duplicated: %s' % identifier)
            return True
        #
        #  3. save into database
        #
        db = self.database
        return await db.save_meta(meta=meta, identifier=identifier)

    # protected
    def check_meta(self, meta: Meta, identifier: ID) -> bool:
        if meta.valid:
            return MetaUtils.match_identifier(identifier=identifier, meta=meta)
        else:
            self.warning(msg='meta error: %s -> %s' % (meta, identifier))

    # Override
    async def save_document(self, document: Document) -> bool:
        #
        #  1. check valid
        #
        valid = await self.check_document(document=document)
        if not valid:
            self.warning(msg='meta not valid: %s' % document.identifier)
            return False
        #
        #  2. check expired
        #
        expired = await self.is_document_expired(document=document)
        if expired:
            self.info(msg='drop expired document: %s' % document)
            return False
        #
        #  3. save into database
        #
        db = self.database
        return await db.save_document(document=document)

    # protected
    async def check_document(self, document: Document) -> bool:
        identifier = document.identifier
        doc_time = document.time
        # check document time
        if doc_time is None:
            self.warning(msg='document without time: %s' % identifier)
        else:
            # calibrate the clock
            # make sure the document time is not in the far future
            near_future = DateTime.current_timestamp() + 30 * 60
            if doc_time > near_future:
                self.error(msg='document time error: %s, %s' % (doc_time, identifier))
                return False
        # check valid
        return await self.verify_document(document=document)

    # protected
    async def verify_document(self, document: Document) -> bool:
        if document.valid:
            return True
        else:
            identifier = document.identifier
        meta = await self.facebook.get_meta(identifier=identifier)
        if meta is None:
            self.warning(msg='failed to get meta: %s' % identifier)
        else:
            return document.verify(public_key=meta.public_key)

    # protected
    async def is_document_expired(self, document: Document) -> bool:
        identifier = document.identifier
        doc_type = DocumentUtils.get_document_type(document=document)
        if doc_type is None:
            doc_type = '*'
        # check old documents with type
        docs = await self.facebook.get_documents(identifier=identifier)
        if docs is None or len(docs) == 0:
            return False
        old = DocumentUtils.last_document(documents=docs, doc_type=doc_type)
        return old is not None and DocumentUtils.is_expired(this_doc=document, old_doc=old)

    # Override
    async def get_meta_key(self, identifier: ID) -> Optional[VerifyKey]:
        meta = await self.facebook.get_meta(identifier=identifier)
        if meta is not None:
            return meta.public_key

    # Override
    async def get_visa_key(self, identifier: ID) -> Optional[EncryptKey]:
        docs = await self.facebook.get_documents(identifier=identifier)
        if docs is None or len(docs) == 0:
            return None
        visa = DocumentUtils.last_visa(documents=docs)
        if visa is not None:
            return visa.public_key

    # Override
    async def local_users(self) -> List[ID]:
        return await self.database.get_local_users()
