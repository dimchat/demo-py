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

from dimsdk import ID, SymmetricKey
from dimplugins import PlainKey

from ..utils import CacheManager
from ..common import CipherKeyDBI


class CipherKeyTable(CipherKeyDBI):
    """ Implementations of CipherKeyDBI """

    CACHE_EXPIRES = 3600*24*7  # seconds

    # noinspection PyUnusedLocal
    def __init__(self, root: str = None, public: str = None, private: str = None):
        super().__init__()
        man = CacheManager()
        self.__keys_cache = man.get_pool(name='cipher_keys')  # (ID, ID) => SymmetricKey

    # noinspection PyMethodMayBeStatic
    def show_info(self):
        print('!!!      cipher key in memory only !!!')

    #
    #   Cipher Key DBI
    #

    # Override
    def cipher_key(self, sender: ID, receiver: ID, generate: bool = False) -> Optional[SymmetricKey]:
        if receiver.is_broadcast:
            return PlainKey()
        now = time.time()
        direction = (sender, receiver)
        key, _ = self.__keys_cache.fetch(key=direction, now=now)
        if key is None and generate:
            # generate and cache it
            key = SymmetricKey.generate(algorithm=SymmetricKey.AES)
            assert key is not None, 'failed to generate symmetric key'
            self.__keys_cache.update(key=direction, value=key, life_span=self.CACHE_EXPIRES, now=now)
        return key

    # Override
    def cache_cipher_key(self, key: SymmetricKey, sender: ID, receiver: ID):
        if receiver.is_broadcast:
            # no need to store cipher key for broadcast message
            return False
        now = time.time()
        direction = (sender, receiver)
        # 1. store into memory cache
        self.__keys_cache.update(key=direction, value=key, life_span=self.CACHE_EXPIRES, now=now)
        return True
