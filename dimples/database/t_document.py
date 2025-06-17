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
from typing import Optional, List

from aiou.mem import CachePool

from dimsdk import ID, Document

from ..utils import Config
from ..common import DocumentDBI

from .dos import DocumentStorage
from .redis import DocumentCache

from .t_base import DbTask, DataCache


class DocTask(DbTask[ID, List[Document]]):

    def __init__(self, identifier: ID, new_document: Optional[Document],
                 redis: DocumentCache, storage: DocumentStorage,
                 mutex_lock: threading.Lock, cache_pool: CachePool):
        super().__init__(mutex_lock=mutex_lock, cache_pool=cache_pool)
        self._identifier = identifier
        self._new_doc = new_document
        self._redis = redis
        self._dos = storage

    @property  # Override
    def cache_key(self) -> ID:
        return self._identifier

    # Override
    async def _read_data(self) -> Optional[List[Document]]:
        # 1. the redis server will return None when cache not found
        # 2. when redis server return an empty array, no need to check local storage again
        docs = await self._redis.load_documents(identifier=self._identifier)
        if docs is not None:
            return docs
        # 3. the local storage will return an empty array, when no document for this id
        docs = await self._dos.load_documents(identifier=self._identifier)
        if docs is None:
            # 4. return empty array as a placeholder for the memory cache
            docs = []
        # 5. update redis server
        await self._redis.save_documents(documents=docs, identifier=self._identifier)
        return docs

    # Override
    async def _write_data(self, documents: List[Document]) -> bool:
        new_doc = self._new_doc
        if new_doc is None:
            assert False, 'should not happen: %s' % self._identifier
            # return False
        else:
            identifier = new_doc.identifier
            doc_type = new_doc.type
        #
        #   0. check old documents
        #
        index = len(documents)
        while index > 0:
            index -= 1
            item = documents[index]
            if not isinstance(item, Document) or item.identifier != identifier:
                self.error(msg='document error: %s, %s' % (identifier, item))
                continue
            elif item.get('type') != doc_type:
                self.info(msg='skip document: %s, type=%s, %s' % (identifier, doc_type, item))
                continue
            elif item == new_doc:
                self.warning(msg='same document, no need to update: %s' % identifier)
                return True
            # old record found, update it
            documents[index] = new_doc
            # break
        if index == 0:
            # same type not found
            documents.append(new_doc)
        #
        #   1. store into redis server
        #
        ok1 = await self._redis.save_documents(documents=documents, identifier=self._identifier)
        #
        #   2. save into local storage
        #
        ok2 = await self._dos.save_documents(documents=documents, identifier=self._identifier)
        return ok1 or ok2


class DocumentTable(DataCache, DocumentDBI):
    """ Implementations of DocumentDBI """

    def __init__(self, config: Config):
        super().__init__(pool_name='documents')  # ID => List[Document]
        self._redis = DocumentCache(config=config)
        self._dos = DocumentStorage(config=config)

    def show_info(self):
        self._dos.show_info()

    def _new_task(self, identifier: ID, new_document: Document = None) -> DocTask:
        return DocTask(identifier=identifier, new_document=new_document,
                       redis=self._redis, storage=self._dos,
                       mutex_lock=self._mutex_lock, cache_pool=self._cache_pool)

    #
    #   Document DBI
    #

    # Override
    async def save_document(self, document: Document) -> bool:
        #
        #   0. check valid
        #
        identifier = document.identifier
        if not document.valid:
            self.error(msg='document not valid: %s' % identifier)
            return False
        #
        #   1. load old records
        #
        task = self._new_task(identifier=identifier)
        docs = await task.load()
        if docs is None:
            docs = []
        else:
            # check time
            new_time = document.time
            if new_time is not None:
                for item in docs:
                    old_time = item.time
                    if old_time is not None and old_time > new_time:
                        self.warning(msg='ignore expired document: %s' % document)
                        return False
        #
        #   2. save new record
        #
        task = self._new_task(identifier=identifier, new_document=document)
        return await task.save(docs)

    # Override
    async def get_documents(self, identifier: ID) -> List[Document]:
        #
        #  build task for loading
        #
        task = self._new_task(identifier=identifier)
        docs = await task.load()
        return [] if docs is None else docs
