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

import time
from typing import Optional

from dimsdk import ID, Document

from ..utils import CacheManager
from ..common import DocumentDBI
from ..common.dbi import is_expired

from .dos import DocumentStorage


class DocumentTable(DocumentDBI):
    """ Implementations of DocumentDBI """

    def __init__(self, root: str = None, public: str = None, private: str = None):
        super().__init__()
        man = CacheManager()
        self.__doc_cache = man.get_pool(name='document')  # ID => Document
        self.__doc_storage = DocumentStorage(root=root, public=public, private=private)

    def show_info(self):
        self.__doc_storage.show_info()

    #
    #   Document DBI
    #

    # Override
    def save_document(self, document: Document) -> bool:
        assert document.valid, 'document invalid: %s' % document
        identifier = document.identifier
        doc_type = document.type
        # 0. check old record with time
        old = self.document(identifier=identifier, doc_type=doc_type)
        if old is not None and is_expired(old_time=old.time, new_time=document.time):
            # document expired, drop it
            return False
        # 1. store into memory cache
        self.__doc_cache.update(key=identifier, value=document, life_span=600)
        # 2. store into local storage
        return self.__doc_storage.save_document(document=document)

    # Override
    def document(self, identifier: ID, doc_type: str = '*') -> Optional[Document]:
        """ get document for ID """
        now = time.time()
        # 1. check memory cache
        value, holder = self.__doc_cache.fetch(key=identifier, now=now)
        if value is None:
            # cache empty
            if holder is None:
                # document not load yet, wait to load
                self.__doc_cache.update(key=identifier, life_span=128, now=now)
            else:
                if holder.is_alive(now=now):
                    # document not exists
                    return None
                # document expired, wait to reload
                holder.renewal(duration=128, now=now)
            # 2. check local storage
            value = self.__doc_storage.document(identifier=identifier, doc_type=doc_type)
            # 3. update memory cache
            self.__doc_cache.update(key=identifier, value=value, life_span=600, now=now)
        # OK, return cached value
        return value
