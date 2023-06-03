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

from mkm.crypto import PrivateKey, SignKey, DecryptKey
from mkm import EntityType, ID
from mkm import Document, Visa

from ..common import AccountDBI
from ..database import PrivateKeyStorage


class AccountInfo:

    def __new__(cls, document: Document, msg_keys: List[PrivateKey] = None):
        if msg_keys is None:
            msg_keys = []
        info = super().__new__(cls)
        info.document = document
        info.msg_keys = msg_keys
        return info

    def show_info(self):
        doc = self.document
        identifier = doc.identifier
        print('!!! ID: %s, document type: %s, name: "%s"' % (identifier, doc.type, doc.name))
        # show algorithm for keys
        msg_keys = self.msg_keys
        array = []
        for key in msg_keys:
            array.append(key.algorithm)
        print('!!! private msg keys: %s' % str(array))

    def save(self, db: AccountDBI) -> bool:
        doc = self.document
        identifier = doc.identifier
        # save keys
        msg_keys = self.msg_keys
        for key in msg_keys:
            db.save_private_key(key=key, user=identifier, key_type=PrivateKeyStorage.MSG_KEY_TAG)
        # save document
        return db.save_document(document=self.document)


def show_document(document: Document):
    name = document.name
    identifier = document.identifier
    print('!!! document type: %s, ID: %s, name: "%s"' % (document.type, identifier, name))
    network = identifier.type
    if network == EntityType.STATION:
        host = document.get_property(key='host')
        port = document.get_property(key='port')
        print('!!! station: %s "%s" (%s:%d)' % (identifier, name, host, port))


def modify_station(document: Document, sign_key: SignKey, msg_keys: List[DecryptKey]) -> AccountInfo:
    # default host, port
    default_host = document.get_property(key='host')
    if default_host is None or len(default_host) == 0:
        default_host = '127.0.0.1'
    default_port = document.get_property(key='port')
    if default_port is None or default_port == 0:
        default_port = 9394
    # get host, port
    host = input('>>> please input station host (default is "%s"): ' % default_host)
    port = input('>>> please input station port (default is %d): ' % default_port)
    host = host.strip()
    port = port.strip()
    # update host, port
    if len(host) > 0:
        document.set_property(key='host', value=host)
    if len(port) > 0:
        port = int(port)
        document.set_property(key='port', value=port)
    # update name & msg keys
    return modify_user(document=document, sign_key=sign_key, msg_keys=msg_keys)


def modify_user(document: Document, sign_key: SignKey, msg_keys: List[DecryptKey]) -> AccountInfo:
    assert isinstance(document, Visa), 'visa error: %s' % document
    visa = document
    # update name, avatar
    default_name = visa.name
    if default_name is None:
        default_name = ''
    default_avatar = visa.avatar
    if default_avatar is None:
        default_avatar = ''
    name = input('>>> please input user name (default is "%s"): ' % default_name)
    if len(name) > 0:
        visa.name = name
    avatar = input('>>> please input avatar url (default is "%s"): ' % default_avatar)
    if len(avatar) > 0:
        visa.avatar = avatar
    print('!!! user info: %s "%s" %s' % (visa.identifier, name, avatar))
    # update msg keys
    if msg_keys is None:
        msg_keys = []
    if not isinstance(sign_key, DecryptKey):
        if msg_keys is None or len(msg_keys) == 0:
            # generate msg key
            pri_key = PrivateKey.generate(algorithm=PrivateKey.RSA)
            msg_keys = [pri_key]
        else:
            pri_key = msg_keys[0]
        visa.key = pri_key.public_key
    # sign
    visa.sign(private_key=sign_key)
    return AccountInfo(document=visa, msg_keys=msg_keys)


def modify_group(document: Document, sign_key: SignKey) -> AccountInfo:
    # TODO: modify bulletin document for group
    pass


def modify(identifier: ID, db: AccountDBI) -> bool:
    print('Modifying DIM account...')
    #
    # Step 1: check meta & private keys
    #
    meta = db.meta(identifier=identifier)
    if meta is None:
        print('!!! meta not exists: %s' % identifier)
        return False
    network = identifier.type
    if EntityType.is_group(network=network):
        # TODO: get group founder(owner) and its id key
        print('!!! TODO: modify bulletin document for group: %s' % identifier)
        return False
    id_key = db.private_key_for_visa_signature(user=identifier)
    if id_key is None:
        print('!!! private key not exists: %s' % identifier)
        return False
    msg_keys = db.private_keys_for_decryption(user=identifier)
    print('!!! old msg keys found: %d, id key: %s' % (len(msg_keys), id_key.algorithm))
    #
    # Step 2: create document
    #
    doc = db.document(identifier=identifier)
    if doc is not None:
        print('!!! old document found: %s' % identifier)
        show_document(document=doc)
        doc = Document.parse(document=doc.copy_dictionary())
    elif EntityType.is_group(network=network):
        doc = Document.create(doc_type=Document.BULLETIN, identifier=identifier)
    else:
        doc = Document.create(doc_type=Document.VISA, identifier=identifier)
    #
    # Step 3: modify document
    #
    if network == EntityType.STATION:
        info = modify_station(document=doc, sign_key=id_key, msg_keys=msg_keys)
    elif EntityType.is_group(network=network):
        info = modify_group(document=doc, sign_key=id_key)
    else:
        info = modify_user(document=doc, sign_key=id_key, msg_keys=msg_keys)
    #
    # Step 3: save account info
    #
    info.show_info()
    return info.save(db=db)
