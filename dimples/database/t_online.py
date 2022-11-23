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
from typing import Set

from dimsdk import ID

from ..utils import CacheManager
from ..common import OnlineDBI


class OnlineTable(OnlineDBI):
    """ Implementations of OnlineDBI """

    # noinspection PyUnusedLocal
    def __init__(self, root: str = None, public: str = None, private: str = None):
        super().__init__()
        man = CacheManager()
        self.__online_cache = man.get_pool(name='session.online_users')  # ID => Set(Tuple)

    # noinspection PyMethodMayBeStatic
    def show_info(self):
        print('!!!    online users in memory only !!!')

    #
    #   Online DBI
    #

    # Override
    def active_users(self) -> Set[ID]:
        users = set()
        now = time.time()
        cache = self.__online_cache
        all_keys = cache.all_keys()
        for identifier in all_keys:
            addresses, _ = cache.fetch(key=identifier, now=now)
            if addresses is not None and len(addresses) > 0:
                users.add(identifier)
        return users

    # Override
    def socket_addresses(self, identifier: ID) -> Set[tuple]:
        now = time.time()
        cache = self.__online_cache
        addresses, _ = cache.fetch(key=identifier, now=now)
        return set() if addresses is None else addresses

    # Override
    def add_socket_address(self, identifier: ID, address: tuple) -> bool:
        now = time.time()
        cache = self.__online_cache
        value, _ = cache.fetch(key=identifier, now=now)
        if value is None:
            value = set()
        value.add(address)
        cache.update(key=identifier, value=value, life_span=36000, now=now)
        return True

    # Override
    def remove_socket_address(self, identifier: ID, address: tuple) -> bool:
        now = time.time()
        cache = self.__online_cache
        value, _ = cache.fetch(key=identifier, now=now)
        if value is None:
            return False
        assert isinstance(value, set), 'socket addresses error: %s' % value
        value.discard(address)
        if len(value) == 0:
            life_span = 0  # let the cache pool remove it automatically
        else:
            life_span = 36000
        cache.update(key=identifier, value=value, life_span=life_span, now=now)
        return True
