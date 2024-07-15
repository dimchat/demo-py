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

import threading
from typing import List, Optional

from aiou.mem import CachePool

from dimsdk import ID, Document, DocumentHelper

from ..utils import SharedCacheManager
from ..common import DocumentDBI

from .dos import DocumentStorage
from .redis import DocumentCache

from .t_base import DbInfo, DbTask


class DocTask(DbTask):

    MEM_CACHE_EXPIRES = 300  # seconds
    MEM_CACHE_REFRESH = 32   # seconds

    def __init__(self, identifier: ID,
                 cache_pool: CachePool, redis: DocumentCache, storage: DocumentStorage,
                 mutex_lock: threading.Lock):
        super().__init__(cache_pool=cache_pool,
                         cache_expires=self.MEM_CACHE_EXPIRES,
                         cache_refresh=self.MEM_CACHE_REFRESH,
                         mutex_lock=mutex_lock)
        self._identifier = identifier
        self._redis = redis
        self._dos = storage

    # Override
    def cache_key(self) -> ID:
        return self._identifier

    # Override
    async def _load_redis_cache(self) -> Optional[List[Document]]:
        # 1. the redis server will return None when cache not found
        # 2. when redis server return an empty array, no need to check local storage again
        return await self._redis.get_documents(identifier=self._identifier)

    # Override
    async def _save_redis_cache(self, value: List[Document]) -> bool:
        return await self._redis.save_documents(documents=value, identifier=self._identifier)

    # Override
    async def _load_local_storage(self) -> Optional[List[Document]]:
        # 1. the local storage will return an empty array, when no document for this id
        # 2. return empty array as a placeholder for the memory cache
        return await self._dos.get_documents(identifier=self._identifier)

    # Override
    async def _save_local_storage(self, value: List[Document]) -> bool:
        return await self._dos.save_documents(documents=value, identifier=self._identifier)


class DocumentTable(DocumentDBI):
    """ Implementations of DocumentDBI """

    def __init__(self, info: DbInfo):
        super().__init__()
        man = SharedCacheManager()
        self._cache = man.get_pool(name='documents')  # ID => List[Document]
        self._redis = DocumentCache(connector=info.redis_connector)
        self._dos = DocumentStorage(root=info.root_dir, public=info.public_dir, private=info.private_dir)
        self._lock = threading.Lock()

    def show_info(self):
        self._dos.show_info()

    def _new_task(self, identifier: ID) -> DocTask:
        return DocTask(identifier=identifier,
                       cache_pool=self._cache, redis=self._redis, storage=self._dos,
                       mutex_lock=self._lock)

    #
    #   Document DBI
    #

    # Override
    async def save_document(self, document: Document) -> bool:
        assert document.valid, 'document invalid: %s' % document
        identifier = document.identifier
        doc_type = document.type
        #
        #  check old documents
        #
        all_documents = await self.get_documents(identifier=identifier)
        old = DocumentHelper.last_document(all_documents, doc_type)
        if old is None and doc_type == Document.VISA:
            old = DocumentHelper.last_document(all_documents, 'profile')
        if old is not None:
            if DocumentHelper.is_expired(document, old):
                # self.warning(msg='drop expired document: %s' % identifier)
                return False
            all_documents.remove(old)
        all_documents.append(document)
        #
        #  build task for saving
        #
        task = self._new_task(identifier=identifier)
        return await task.save(value=all_documents)

    # Override
    async def get_documents(self, identifier: ID) -> List[Document]:
        #
        #  build task for loading
        #
        task = self._new_task(identifier=identifier)
        docs = await task.load()
        return [] if docs is None else docs
