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

from mkm.crypto import PrivateKey
from mkm import ID

from .storage import Storage
from .storage import template_replace


class PrivateKeyStorage(Storage):
    """
        Private Key Storage
        ~~~~~~~~~~~~~~~~~~~
        (1) Identify Key - paired to meta.key, CONSTANT
            file path: '.dim/private/{ADDRESS}/secret.js'
        (2) Message Keys - paired to visa.key, VOLATILE
            file path: '.dim/private/{ADDRESS}/secret_keys.js'
    """
    id_key_path = '{PRIVATE}/{ADDRESS}/secret.js'
    msg_keys_path = '{PRIVATE}/{ADDRESS}/secret_keys.js'

    def show(self):
        path1 = template_replace(self.id_key_path, 'PRIVATE', self._private)
        path2 = template_replace(self.msg_keys_path, 'PRIVATE', self._private)
        print('!!!    id key path: %s' % path1)
        print('!!!  msg keys path: %s' % path2)

    def __id_key_path(self, identifier: ID) -> str:
        path = self.id_key_path
        path = template_replace(path, 'PRIVATE', self._private)
        return template_replace(path, 'ADDRESS', str(identifier.address))

    def __msg_keys_path(self, identifier: ID) -> str:
        path = self.msg_keys_path
        path = template_replace(path, 'PRIVATE', self._private)
        return template_replace(path, 'ADDRESS', str(identifier.address))

    def save_id_key(self, key: PrivateKey, identifier: ID) -> bool:
        path = self.__id_key_path(identifier=identifier)
        self.info('Saving identity private key into: %s' % path)
        return self.write_json(container=key.dictionary, path=path)

    def load_id_key(self, identifier: ID) -> Optional[PrivateKey]:
        path = self.__id_key_path(identifier=identifier)
        self.info('Loading identity private key from: %s' % path)
        info = self.read_json(path=path)
        if info is not None:
            return PrivateKey.parse(key=info)

    def save_msg_key(self, key: PrivateKey, identifier: ID) -> bool:
        private_keys = self.load_msg_keys(identifier=identifier)
        private_keys = insert_key(key=key, private_keys=private_keys)
        if private_keys is None:
            # nothing changed
            return False
        plain = [item.dictionary for item in private_keys]
        path = self.__msg_keys_path(identifier=identifier)
        self.info('Saving message private keys into: %s' % path)
        return self.write_json(container=plain, path=path)

    def load_msg_keys(self, identifier: ID) -> List[PrivateKey]:
        keys = []
        path = self.__msg_keys_path(identifier=identifier)
        self.info('Loading message private keys from: %s' % path)
        array = self.read_json(path=path)
        if array is not None:
            for item in array:
                k = PrivateKey.parse(key=item)
                if k is not None:
                    keys.append(k)
        return keys


def insert_key(key: PrivateKey, private_keys: List[PrivateKey]) -> Optional[List[PrivateKey]]:
    index = find_key(key=key, private_keys=private_keys)
    if index == 0:
        return None  # nothing changed
    elif index > 0:
        private_keys.pop(index)  # move to the front
    elif len(private_keys) > 2:
        private_keys.pop()  # keep only last three records
    private_keys.insert(0, key)
    return private_keys


def find_key(key, private_keys: List[PrivateKey]) -> int:
    index = 0
    data = key.get('data')
    for item in private_keys:
        if item.get('data') == data:
            return index
        else:
            index += 1
    return -1