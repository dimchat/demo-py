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

from typing import Optional, List

from mkm.crypto import PrivateKey, DecryptKey, SignKey
from mkm import ID, Meta, Document

from .t_meta import TableMeta
from .t_document import TableDocument
from .t_private import TablePrivateKey


class AccountDatabase:
    """
        Database for MingKeMing
        ~~~~~~~~~~~~~~~~~~~~~~~
    """

    def __init__(self, root: str = None, public: str = None, private: str = None):
        super().__init__()
        self.__t_meta = TableMeta(root=root, public=public, private=private)
        self.__t_doc = TableDocument(root=root, public=public, private=private)
        self.__t_private = TablePrivateKey(root=root, public=public, private=private)

    def show_info(self):
        self.__t_meta.show_info()
        self.__t_doc.show_info()
        self.__t_private.show_info()

    #
    #   Meta
    #
    def save_meta(self, meta: Meta, identifier: ID) -> bool:
        return self.__t_meta.save_meta(meta=meta, identifier=identifier)

    def meta(self, identifier: ID) -> Optional[Meta]:
        return self.__t_meta.meta(identifier=identifier)

    #
    #   Document
    #
    def save_document(self, document: Document) -> bool:
        return self.__t_doc.save_document(document=document)

    def document(self, identifier: ID, doc_type: Optional[str] = '*') -> Optional[Document]:
        return self.__t_doc.document(identifier=identifier, doc_type=doc_type)

    #
    #   Private Keys
    #
    def save_private_key(self, key: PrivateKey, identifier: ID, key_type: str = 'M') -> bool:
        return self.__t_private.save_private_key(key=key, identifier=identifier, key_type=key_type)

    def private_keys_for_decryption(self, identifier: ID) -> List[DecryptKey]:
        return self.__t_private.private_keys_for_decryption(identifier=identifier)

    def private_key_for_signature(self, identifier: ID) -> Optional[SignKey]:
        return self.__t_private.private_key_for_signature(identifier=identifier)

    def private_key_for_visa_signature(self, identifier: ID) -> Optional[SignKey]:
        return self.__t_private.private_key_for_visa_signature(identifier=identifier)
