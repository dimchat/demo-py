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

from typing import List

from mkm.crypto import PrivateKey, SignKey
from mkm.protocol import entity_is_group, meta_has_seed
from mkm import EntityType, ID
from mkm import MetaType, Meta
from mkm import Document, Visa, Bulletin

from dimplugins.network import NetworkType, network_to_type

from ..database.account import ID_KEY_TAG, MSG_KEY_TAG
from ..database import AccountDatabase


class AccountInfo:

    def __new__(cls, identifier: ID, meta: Meta, document: Document,
                private_key: PrivateKey = None, msg_keys: List[PrivateKey] = None):
        if msg_keys is None:
            msg_keys = []
        info = super().__new__(cls)
        info.identifier = identifier
        info.meta = meta
        info.document = document
        info.private_key = private_key
        info.msg_keys = msg_keys
        return info

    def show(self):
        identifier = self.identifier
        meta = self.meta
        doc = self.document
        print('!!! ID: %s, meta type: %d, document type: %s, name: "%s"' % (identifier, meta.type, doc.type, doc.name))
        # show algorithm for keys
        private_key = self.private_key
        if private_key is not None:
            msg_keys = self.msg_keys
            array = []
            for key in msg_keys:
                array.append(key.algorithm)
            print('!!! private key: %s, msg keys: %s' % (private_key.algorithm, array))

    def save(self, db: AccountDatabase) -> bool:
        identifier = self.identifier
        # save keys
        private_key = self.private_key
        if private_key is not None:
            db.save_private_key(key=private_key, identifier=identifier, key_type=ID_KEY_TAG)
        msg_keys = self.msg_keys
        for key in msg_keys:
            db.save_private_key(key=key, identifier=identifier, key_type=MSG_KEY_TAG)
        # save meta & document
        db.save_meta(meta=self.meta, identifier=identifier)
        return db.save_document(document=self.document)


id_types = [
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


def input_type(candidates: list, name: str) -> int:
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


def gen_station(network: int, seed: str) -> AccountInfo:
    private_key = PrivateKey.generate(algorithm=PrivateKey.RSA)
    meta = Meta.generate(version=MetaType.DEFAULT, key=private_key, seed=seed)
    identifier = ID.generate(meta=meta, network=network)
    # document for station
    doc = Document.create(doc_type=Document.VISA, identifier=identifier)
    assert isinstance(doc, Visa), 'document error: %s' % doc
    doc.key = private_key.public_key
    name = input('>>> please input station name: ')
    doc.name = name
    host = input('>>> please input station host: ')
    port = input('>>> please input station port: ')
    host = host.strip()
    port = int(port)
    doc.set_property(key='host', value=host)
    doc.set_property(key='port', value=port)
    print('!!! station info: %s "%s" (%s:%d)' % (identifier, name, host, port))
    # sign
    doc.sign(private_key=private_key)
    return AccountInfo(identifier=identifier, meta=meta, document=doc, private_key=private_key)


def gen_user(network: int, version: int, seed: str) -> AccountInfo:
    if version == MetaType.DEFAULT:
        id_private_key = PrivateKey.generate(algorithm=PrivateKey.RSA)
        msg_private_key = id_private_key
    else:
        id_private_key = PrivateKey.generate(algorithm=PrivateKey.ECC)
        msg_private_key = PrivateKey.generate(algorithm=PrivateKey.RSA)
    meta = Meta.generate(version=version, key=id_private_key, seed=seed)
    identifier = ID.generate(meta=meta, network=network)
    # document for user
    doc = Document.create(doc_type=Document.VISA, identifier=identifier)
    assert isinstance(doc, Visa), 'visa error: %s' % doc
    doc.key = msg_private_key.public_key
    name = input('>>> please input user name: ')
    doc.name = name
    print('!!! user info: %s "%s"' % (identifier, name))
    # sign
    doc.sign(private_key=id_private_key)
    if msg_private_key == id_private_key:
        keys = []
    else:
        keys = [msg_private_key]
    return AccountInfo(identifier=identifier, meta=meta, document=doc, private_key=id_private_key, msg_keys=keys)


def gen_group(network: int, seed: str, founder: ID, sign_key: SignKey) -> AccountInfo:
    meta = Meta.generate(version=MetaType.DEFAULT, key=sign_key, seed=seed)
    identifier = ID.generate(meta=meta, network=network)
    # document for station
    doc = Document.create(doc_type=Document.BULLETIN, identifier=identifier)
    assert isinstance(doc, Bulletin), 'bulletin error: %s' % doc
    name = input('>>> please input group name: ')
    doc.name = name
    print('!!! group info: %s "%s", founder: %s' % (identifier, name, founder))
    # sign
    doc.sign(private_key=sign_key)
    return AccountInfo(identifier=identifier, meta=meta, document=doc)


def generate(db: AccountDatabase) -> bool:
    print('Generating DIM account...')
    db.show()
    #
    # Step 1: get entity type
    #
    network = input_type(candidates=id_types, name='address type')
    print('!!! address type: %d' % network)
    #
    # Step 2: get meta type
    #
    if network in [EntityType.USER, NetworkType.MAIN]:
        version = input_type(candidates=[
            (MetaType.BTC, 'BTC'),
            (MetaType.ETH, 'ETH'),
        ], name='meta type')
    else:
        version = MetaType.DEFAULT.value
    print('!!! meta type: %d' % version)
    #
    # Step 3: get meta seed (ID.name)
    #
    if network in [EntityType.STATION, NetworkType.STATION]:
        default_seed = 'station'
    elif network in [EntityType.BOT, NetworkType.BOT]:
        default_seed = 'bot'
    elif entity_is_group(network=network_to_type(network=network)):
        default_seed = 'group'
    elif meta_has_seed(version=version):
        default_seed = 'user'
    else:
        # BTC/ETH address as ID without seed
        default_seed = None
    if default_seed is None:
        seed = None
    else:
        seed = input('>>> please input ID.name (default is "%s"): ' % default_seed)
        seed = seed.strip()
        if len(seed) == 0:
            seed = default_seed
        print('!!! meta seed: %s' % seed)
    #
    # Step 4: generate account info
    #
    if network in [EntityType.STATION, NetworkType.STATION]:
        info = gen_station(network=network, seed=seed)
    elif entity_is_group(network=network_to_type(network=network)):
        fid = input('>>> please input founder ID: ')
        founder = ID.parse(identifier=fid)
        assert founder is not None and founder.is_user, 'group founder error: %s' % fid
        sign_key = db.private_key_for_visa_signature(identifier=founder)
        assert sign_key is not None, 'founder private key not found: %s' % founder
        info = gen_group(network=network, seed=seed, founder=founder, sign_key=sign_key)
    else:
        info = gen_user(network=network, version=version, seed=seed)
    #
    # Step 5: save account info
    #
    info.show()
    return info.save(db=db)
