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

from dimsdk import PrivateKey, SignKey, DecryptKey
from dimsdk import ID

from ...utils import template_replace
from ...common import PrivateKeyDBI

from .base import Storage


class PrivateKeyStorage(Storage, PrivateKeyDBI):
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

    """
        Key Tags
        ~~~~~~~~
    """
    ID_KEY_TAG = 'M'  # private key pared to meta.key
    MSG_KEY_TAG = 'V'  # private key pared to visa.key

    def show_info(self):
        path1 = self.private_path(self.id_key_path)
        path2 = self.private_path(self.msg_keys_path)
        print('!!!         id key path: %s' % path1)
        print('!!!       msg keys path: %s' % path2)

    def __id_key_path(self, identifier: ID) -> str:
        path = self.private_path(self.id_key_path)
        return template_replace(path, key='ADDRESS', value=str(identifier.address))

    def __msg_keys_path(self, identifier: ID) -> str:
        path = self.private_path(self.msg_keys_path)
        return template_replace(path, key='ADDRESS', value=str(identifier.address))

    async def _save_id_key(self, key: PrivateKey, identifier: ID) -> bool:
        path = self.__id_key_path(identifier=identifier)
        self.info(msg='Saving identity private key into: %s' % path)
        return await self.write_json(container=key.dictionary, path=path)

    async def _load_id_key(self, identifier: ID) -> Optional[PrivateKey]:
        path = self.__id_key_path(identifier=identifier)
        self.info(msg='Loading identity private key from: %s' % path)
        info = await self.read_json(path=path)
        if info is None:
            # file not found
            self.warning(msg='id key file not found: %s' % path)
        else:
            return PrivateKey.parse(key=info)

    async def _save_msg_key(self, key: PrivateKey, identifier: ID) -> bool:
        private_keys = await self._load_msg_keys(identifier=identifier)
        private_keys = PrivateKeyDBI.insert(item=key, array=private_keys)
        if private_keys is None:
            # nothing changed
            return False
        plain = [item.dictionary for item in private_keys]
        path = self.__msg_keys_path(identifier=identifier)
        self.info(msg='Saving message private keys into: %s' % path)
        return await self.write_json(container=plain, path=path)

    async def _load_msg_keys(self, identifier: ID) -> List[PrivateKey]:
        keys = []
        path = self.__msg_keys_path(identifier=identifier)
        self.info(msg='Loading message private keys from: %s' % path)
        array = await self.read_json(path=path)
        if array is None:
            # file not found
            self.warning(msg='msg key file not found: %s' % path)
        else:
            for item in array:
                k = PrivateKey.parse(key=item)
                if k is not None:
                    keys.append(k)
        return keys

    #
    #   PrivateKey DBI
    #

    # Override
    async def save_private_key(self, key: PrivateKey, user: ID, key_type: str = 'M') -> bool:
        if key_type == self.ID_KEY_TAG:
            # save private key for meta
            return await self._save_id_key(key=key, identifier=user)
        else:
            # save private key for visa
            return await self._save_msg_key(key=key, identifier=user)

    # Override
    async def private_keys_for_decryption(self, user: ID) -> List[DecryptKey]:
        keys: list = await self._load_msg_keys(identifier=user)
        # the 'ID key' could be used for encrypting message too (RSA),
        # so we append it to the decrypt keys here
        id_key = await self._load_id_key(identifier=user)
        if isinstance(id_key, DecryptKey) and PrivateKeyDBI.find(item=id_key, array=keys) < 0:
            keys.append(id_key)
        return keys

    # Override
    async def private_key_for_signature(self, user: ID) -> Optional[SignKey]:
        # TODO: support multi private keys
        return await self.private_key_for_visa_signature(user=user)

    # Override
    async def private_key_for_visa_signature(self, user: ID) -> Optional[SignKey]:
        return await self._load_id_key(identifier=user)
