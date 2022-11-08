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

from .t_meta import MetaStorage
from .t_doc import DocumentStorage
from .t_keys import PrivateKeyStorage
from .t_keys import find_key


class AccountDatabase:
    """
        Database for MingKeMing
        ~~~~~~~~~~~~~~~~~~~~~~~
    """

    def __init__(self, root: str = None, public: str = None, private: str = None):
        super().__init__()
        self.__meta_storage = MetaStorage(root=root, public=public, private=private)
        self.__doc_storage = DocumentStorage(root=root, public=public, private=private)
        self.__key_storage = PrivateKeyStorage(root=root, public=public, private=private)

    def show(self):
        self.__meta_storage.show()
        self.__doc_storage.show()
        self.__key_storage.show()

    #
    #   Meta
    #
    def save_meta(self, meta: Meta, identifier: ID) -> bool:
        return self.__meta_storage.save_meta(meta=meta, identifier=identifier)

    def load_meta(self, identifier: ID) -> Optional[Meta]:
        return self.__meta_storage.load_meta(identifier=identifier)

    #
    #   Document
    #
    def save_document(self, document: Document) -> bool:
        return self.__doc_storage.save_document(document=document)

    def load_document(self, identifier: ID, doc_type: Optional[str] = '*') -> Optional[Document]:
        return self.__doc_storage.load_document(identifier=identifier, doc_type=doc_type)

    #
    #   Private Keys
    #
    def save_private_key(self, key: PrivateKey, identifier: ID, key_type: str = 'M') -> bool:
        if key_type == ID_KEY_TAG:
            # save private key for meta
            return self.__key_storage.save_id_key(key=key, identifier=identifier)
        else:
            # save private key for visa
            return self.__key_storage.save_msg_key(key=key, identifier=identifier)

    def private_keys_for_decryption(self, identifier: ID) -> List[DecryptKey]:
        keys: list = self.__key_storage.load_msg_keys(identifier=identifier)
        # the 'ID key' could be used for encrypting message too (RSA),
        # so we append it to the decrypt keys here
        id_key = self.__key_storage.load_id_key(identifier=identifier)
        if isinstance(id_key, DecryptKey) and find_key(key=id_key, private_keys=keys) < 0:
            keys.append(id_key)
        return keys

    def private_key_for_signature(self, identifier: ID) -> Optional[SignKey]:
        # TODO: support multi private keys
        return self.private_key_for_visa_signature(identifier=identifier)

    def private_key_for_visa_signature(self, identifier: ID) -> Optional[SignKey]:
        return self.__key_storage.load_id_key(identifier=identifier)


ID_KEY_TAG = 'M'   # private key pared to meta.key
MSG_KEY_TAG = 'V'  # private key pared to visa.key
