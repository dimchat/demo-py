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

from abc import ABC, abstractmethod
from typing import Optional, Tuple, List

from dimsdk import SignKey
from dimsdk import EntityType, ID
from dimsdk import MetaType, Meta
from dimsdk import Document

from ..utils import Logging
from ..common import AccountDBI
from ..common.compat import NetworkType, network_to_type


class BaseAccount(Logging, ABC):

    ID_TYPES = [
        (EntityType.USER,       'User'),
        (EntityType.GROUP,      'Group (User Group)'),
        (EntityType.STATION,    'Station (Server Node)'),
        (EntityType.ISP,        'ISP (Service Provider)'),
        (EntityType.BOT,        'Bot (Business Node)'),
        (EntityType.ICP,        'ICP (Content Provider)'),
        (EntityType.SUPERVISOR, 'Supervisor (Company President)'),
        (EntityType.COMPANY,    'Company (Super Group for ISP/ICP)'),

        (NetworkType.MAIN,    'User (Deprecated)'),
        (NetworkType.GROUP,   'Group (Deprecated)'),
        (NetworkType.STATION, 'Station (Deprecated)'),
        (NetworkType.BOT,     'Bot (Deprecated)'),
    ]

    USER_META_TYPES = [
        (MetaType.BTC, 'BTC'),
        (MetaType.ETH, 'ETH'),
    ]
    DEFAULT_META_TYPE = MetaType.DEFAULT.value

    def __init__(self, database: AccountDBI):
        super().__init__()
        self.__db = database
        self.__id: Optional[ID] = None
        self.__meta: Optional[Meta] = None
        self.__doc: Optional[Document] = None

    @property
    def database(self) -> AccountDBI:
        return self.__db

    @property
    def identifier(self) -> Optional[ID]:
        return self.__id

    @classmethod
    def input_type(cls, candidates: list, name: str) -> int:
        print('--- %s(s) ---' % name)
        for candy in candidates:
            print('% 5d: %s' % candy)
        while True:
            try:
                a = input('>>> please input %s: ' % name)
                v = int(a)
                for candy in candidates:
                    if v == candy[0]:
                        return v
                print('!!! %s error: %s' % (name, a))
            except Exception as e:
                print(e)

    @classmethod
    def get_address_type(cls) -> int:
        network = cls.input_type(candidates=cls.ID_TYPES, name='address type')
        print('!!! address type: %d' % network)
        return network

    @classmethod
    def get_meta_type(cls, address_type: int) -> int:
        if address_type in [EntityType.USER, NetworkType.MAIN]:
            version = cls.input_type(candidates=cls.USER_META_TYPES, name='meta type')
        else:
            version = cls.DEFAULT_META_TYPE
        print('!!! meta type: %d' % version)
        return version

    @classmethod
    def get_meta_seed(cls, meta_type: int, address_type: int) -> Optional[str]:
        if not MetaType.has_seed(version=meta_type):
            # BTC/ETH address as ID without seed
            return None
        address_type = network_to_type(network=address_type)
        if address_type == EntityType.STATION:
            default_seed = 'test_station'
        elif address_type == EntityType.BOT:
            default_seed = 'test_bot'
        elif EntityType.is_group(network=address_type):
            default_seed = 'test_group'
        else:
            default_seed = 'test_user'
        seed = input('>>> please input ID.name (default is "%s"): ' % default_seed)
        seed = seed.strip()
        if len(seed) == 0:
            seed = default_seed
        else:
            assert seed.find(' ') < 0, 'ID.name cannot contain spaces.'
        print('!!! ID.name (meta seed): %s' % seed)
        return seed

    def show_info(self):
        identifier = self.__id
        meta = self.__meta
        doc = self.__doc
        print('!!!')
        print('!!! ID: %s' % identifier)
        print('!!!')
        print('!!! meta type: %d, document type: %s, name: "%s"' % (meta.type, doc.type, doc.name))
        print('!!!')

    def load_info(self, identifier: ID) -> Tuple[Optional[Meta], Optional[Document]]:
        assert self.__id is None, 'ID exists: %s' % self.__id
        assert self.__meta is None, 'meta exists: %s' % self.__meta
        assert self.__doc is None, 'document exists: %s' % self.__doc
        db = self.__db
        meta = db.meta(identifier=identifier)
        if meta is None:
            self.error(msg='failed to load meta: %s' % identifier)
            return None, None
        doc = db.document(identifier=identifier)
        if doc is None:
            self.error(msg='failed to load document: %s' % identifier)
            return meta, None
        self.__id = identifier
        self.__meta = meta
        self.__doc = doc
        return meta, doc

    def save_meta(self) -> Optional[Tuple[ID, Meta]]:
        identifier = self.__id
        meta = self.__meta
        db = self.__db
        if db.save_meta(meta=meta, identifier=identifier):
            return identifier, meta
        else:
            self.error(msg='failed to save meta: %s, %s' % (identifier, meta))

    def save_document(self) -> Optional[Document]:
        doc = self.__doc
        db = self.__db
        if db.save_document(document=doc):
            return doc
        else:
            self.error(msg='failed to save document: %s, %s' % (doc.identifier, doc))

    def update(self, exists: bool = False) -> Optional[Document]:
        doc = self.edit()
        assert doc is not None, 'failed to edit document'
        # TODO: sign & save
        return doc

    @abstractmethod
    def edit(self) -> Optional[Document]:
        """ edit properties """
        raise NotImplemented

    @abstractmethod
    def generate(self, network: int, version: int, seed: Optional[str]) -> Document:
        raise NotImplemented

    # protected
    def generate_meta(self, version: int, seed: Optional[str], sign_key: SignKey) -> Meta:
        """ 1. generate meta with sign key """
        assert self.__meta is None, 'meta exists: %s' % self.__meta
        self.__meta = Meta.generate(version=version, private_key=sign_key, seed=seed)
        return self.__meta

    # protected
    def generate_identifier(self, network: int) -> ID:
        """ 2. generate id with meta """
        assert self.__id is None, 'ID exists: %s' % self.__id
        self.__id = ID.generate(meta=self.__meta, network=network)
        return self.__id

    # protected
    def generate_document(self, doc_type: str) -> Document:
        """ 3. generate document with id """
        assert self.__doc is None, 'document exists: %s' % self.__doc
        self.__doc = Document.create(doc_type=doc_type, identifier=self.__id)
        return self.__doc

    # protected
    def edit_properties(self, fields: List[Tuple[str, str, str, str]]) -> Document:
        """ 4. edit properties in document """
        identifier = self.__id
        doc = self.__doc
        assert doc.identifier == identifier, 'document error: %s, %s' % (identifier, doc)
        print('!!!')
        print('!!! ========================================================================')
        print('!!!   Editing document for: %s' % identifier)
        print('!!! ------------------------------------------------------------------------')
        print('!!!')
        for item in fields:
            name = item[0]
            desc = item[1]
            kind = item[2]
            old_value = doc.get_property(key=name)
            if old_value is None:
                old_value = item[3]
            # input new value
            if kind == 'str':
                value = input('>>>   please input %s (default is "%s"): ' % (desc, old_value))
            else:
                value = input('>>>   please input %s (default is %s): ' % (desc, old_value))
            value = value.strip()
            if len(value) == 0:
                value = old_value
            elif kind == 'int':
                value = int(value)
            print('<<<   %s = %s;' % (name, value))
            print('!!!')
            doc.set_property(key=name, value=value)
        print('!!! ------------------------------------------------------------------------')
        print('!!!   Done!')
        print('!!! ========================================================================')
        print('!!!')
        return doc

    """ Fields of document properties """
    USER_FIELDS = [
        # key          description     type   default
        ('name',       'user name',    'str', 'Satoshi Nakamoto'),
        ('avatar',     'avatar url',   'str', ''),
    ]
    BOT_FIELDS = [
        # key          description     type   default
        ('name',       'bot name',     'str', 'Service Bot'),
        ('avatar',     'avatar url',   'str', ''),
    ]
    STATION_FIELDS = [
        # key          description     type   default
        ('name',       'station name', 'str', 'Base Station'),
        ('host',       'station host', 'str', '127.0.0.1'),
        ('port',       'station port', 'int', 9394),
    ]
    GROUP_FIELDS = [
        # key         description      type   default
        ('name',      'group name',    'str', 'Group Chat'),
        ('assistant', 'group bot',     'str', ''),
    ]
