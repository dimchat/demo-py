# -*- coding: utf-8 -*-
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

from typing import Optional, Tuple, List

from mkm.crypto import PrivateKey, SignKey
from mkm import ID
from mkm import Meta
from mkm import Document, Visa, Bulletin

from ..common import AccountDBI
from ..database import PrivateKeyStorage

from .base import BaseAccount


class GroupAccount(BaseAccount):

    def __init__(self, database: AccountDBI):
        super().__init__(database=database)
        self.__founder: Optional[ID] = None
        # founder's private keys
        self.__id_pri_key: Optional[PrivateKey] = None

    # Override
    def show_info(self):
        super().show_info()
        # show algorithm for keys
        id_key = self.__id_pri_key
        algor = None if id_key is None else id_key.algorithm
        print('!!! founder: %s, private key: %s' % (self.__founder, algor))
        print('!!!')

    def get_founder(self) -> Optional[ID]:
        assert self.__founder is None, 'founder exists: %s' % self.__founder
        value = input('>>> please input group founder: ')
        value = value.strip()
        if len(value) > 0:
            self.__founder = ID.parse(identifier=value)
        return self.__founder

    def load_founder(self, founder: ID) -> Optional[SignKey]:
        assert self.__founder is None or self.__founder == founder, 'another founder exists: %s' % self.__founder
        assert self.__id_pri_key is None, 'private key exists: %s' % self.__id_pri_key
        db = self.database
        id_key = db.private_key_for_visa_signature(user=founder)
        if id_key is None:
            self.error(msg='failed to load id key: %s' % founder)
            return None
        self.__founder = founder
        self.__id_pri_key = id_key
        return id_key

    # Override
    def generate(self, network: int, version: int, seed: Optional[str]) -> Document:
        id_pri_key = self.__id_pri_key
        meta = self.generate_meta(version=version, seed=seed, sign_key=id_pri_key)
        assert meta is not None, 'failed to generate meta'
        identifier = self.generate_identifier(network=network)
        doc = self.generate_document(doc_type=Document.BULLETIN)
        assert doc.identifier == identifier, 'ID not match: %s' % identifier
        return doc

    # Override
    def update(self, exists: bool = False) -> Optional[Document]:
        doc = self.edit()
        assert isinstance(doc, Bulletin), 'failed to edit bulletin: %s' % doc
        # check founder & sign
        founder = doc.founder
        if founder is None:
            founder = self.__founder
            assert founder is not None, 'founder not found'
            doc.set_property(key='founder', value=str(founder))
        if doc.sign(private_key=self.__id_pri_key) is None:
            return None
        if not exists:
            self.save_meta()
        return self.save_document()

    # protected
    def edit(self) -> Optional[Document]:
        return self.edit_properties(fields=self.GROUP_FIELDS)


class UserAccount(BaseAccount):

    def __init__(self, database: AccountDBI):
        super().__init__(database=database)
        # private keys
        self.__id_pri_key: Optional[PrivateKey] = None
        self.__msg_pri_keys: Optional[List[PrivateKey]] = None

    # Override
    def load_info(self, identifier: ID) -> Tuple[Optional[Meta], Optional[Document]]:
        db = self.database
        id_key = db.private_key_for_visa_signature(user=identifier)
        if id_key is None:
            self.error(msg='failed to load id key: %s' % identifier)
            return None, None
        msg_keys = db.private_keys_for_decryption(user=identifier)
        if len(msg_keys) == 0:
            self.error(msg='failed to load msg keys: %s' % identifier)
            return None, None
        meta, doc = super().load_info(identifier=identifier)
        if doc is None:
            return meta, None
        self.__id_pri_key = id_key
        self.__msg_pri_keys = msg_keys
        return meta, doc

    # Override
    def show_info(self):
        super().show_info()
        # show algorithm for keys
        id_key = self.__id_pri_key
        msg_keys = self.__msg_pri_keys
        algor = None if id_key is None else id_key.algorithm
        array = [] if msg_keys is None else [key.algorithm for key in msg_keys]
        print('!!! private key: %s, msg keys: %s' % (algor, array))
        print('!!!')

    def save_private_keys(self) -> Tuple[PrivateKey, List[PrivateKey]]:
        id_pri_key = self.__id_pri_key
        msg_pri_keys = self.__msg_pri_keys
        assert id_pri_key is not None and len(msg_pri_keys) > 0, 'private keys not found'
        identifier = self.identifier
        assert identifier is not None, 'ID not found'
        db = self.database
        db.save_private_key(key=id_pri_key, user=identifier, key_type=PrivateKeyStorage.ID_KEY_TAG)
        for s_key in msg_pri_keys:
            db.save_private_key(key=s_key, user=identifier, key_type=PrivateKeyStorage.MSG_KEY_TAG)
        return id_pri_key, msg_pri_keys

    # private
    def generate_keys(self) -> Tuple[PrivateKey, List[PrivateKey]]:
        if self.__id_pri_key is None:
            self.__id_pri_key = PrivateKey.generate(algorithm=PrivateKey.ECC)
        if self.__msg_pri_keys is None:
            self.__msg_pri_keys = [PrivateKey.generate(algorithm=PrivateKey.RSA)]
        return self.__id_pri_key, self.__msg_pri_keys

    # Override
    def generate(self, network: int, version: int, seed: Optional[str]) -> Visa:
        id_pri_key, msg_pri_keys = self.generate_keys()
        meta = self.generate_meta(version=version, seed=seed, sign_key=id_pri_key)
        assert meta is not None, 'failed to generate meta'
        identifier = self.generate_identifier(network=network)
        doc = self.generate_document(doc_type=Document.VISA)
        assert isinstance(doc, Visa), 'visa error: %s' % doc
        assert doc.identifier == identifier, 'ID not match: %s' % identifier
        return doc

    # Override
    def update(self, exists: bool = False) -> Optional[Document]:
        doc = self.edit()
        assert isinstance(doc, Visa), 'failed to edit visa: %s' % doc
        # update visa.key and sign
        doc.key = self.__msg_pri_keys[0].public_key
        if doc.sign(private_key=self.__id_pri_key) is None:
            return None
        if not exists:
            self.save_private_keys()
            self.save_meta()
        return self.save_document()

    # protected
    def edit(self) -> Optional[Document]:
        return self.edit_properties(fields=self.USER_FIELDS)


class BotAccount(UserAccount):

    # Override
    def edit(self) -> Optional[Document]:
        return self.edit_properties(fields=self.BOT_FIELDS)


class StationAccount(UserAccount):

    # Override
    def edit(self) -> Optional[Document]:
        return self.edit_properties(fields=self.STATION_FIELDS)
