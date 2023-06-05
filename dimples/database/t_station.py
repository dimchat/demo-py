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
from typing import Optional, List

from dimsdk import ID

from ..utils import CacheManager
from ..common import ProviderInfo, StationInfo
from ..common import ProviderDBI, StationDBI

from .dos import StationStorage


class StationTable(ProviderDBI, StationDBI):
    """ Implementations of ProviderDBI """

    # noinspection PyUnusedLocal
    def __init__(self, root: str = None, public: str = None, private: str = None):
        super().__init__()
        man = CacheManager()
        self.__dim_cache = man.get_pool(name='dim')            # 'providers' => List[ProviderInfo]
        self.__stations_cache = man.get_pool(name='stations')  # SP_ID => List[StationInfo]
        self.__station_storage = StationStorage(root=root, public=public, private=private)

    # noinspection PyMethodMayBeStatic
    def show_info(self):
        self.__station_storage.show_info()

    #
    #   Provider DBI
    #

    # Override
    def all_providers(self) -> List[ProviderInfo]:
        """ get providers """
        now = time.time()
        # 1. check memory cache
        value, holder = self.__dim_cache.fetch(key='providers', now=now)
        if value is None:
            # cache empty
            if holder is None:
                # cache not load yet, wait for loading
                self.__dim_cache.update(key='providers', life_span=128, now=now)
            else:
                if holder.is_alive(now=now):
                    # cache not exists
                    return []
                # cache expired, wait for reloading
                holder.renewal(duration=128, now=now)
            # 2. check local storage
            value = self.__station_storage.all_providers()
            if value is None or len(value) == 0:
                value = [ProviderInfo(identifier=ProviderInfo.GSP, chosen=0)]
            # 3. update memory cache
            self.__dim_cache.update(key='providers', value=value, life_span=600, now=now)
        # OK, return cached value
        return value

    # Override
    def add_provider(self, identifier: ID, chosen: int = 0) -> bool:
        # 1. clear cache to reload
        self.__dim_cache.erase(key='providers')
        # 2. store into local storage
        return self.__station_storage.add_provider(identifier=identifier, chosen=chosen)

    # Override
    def update_provider(self, identifier: ID, chosen: int) -> bool:
        # 1. clear cache to reload
        self.__dim_cache.erase(key='providers')
        # 2. store into local storage
        return self.__station_storage.update_provider(identifier=identifier, chosen=chosen)

    # Override
    def remove_provider(self, identifier: ID) -> bool:
        # 1. clear cache to reload
        self.__dim_cache.erase(key='providers')
        # 2. store into local storage
        return self.__station_storage.remove_provider(identifier=identifier)

    #
    #   Station DBI
    #

    # Override
    def all_stations(self, provider: ID) -> List[StationInfo]:
        """ get stations with SP ID """
        now = time.time()
        # 1. check memory cache
        value, holder = self.__stations_cache.fetch(key=provider, now=now)
        if value is None:
            # cache empty
            if holder is None:
                # cache not load yet, wait for loading
                self.__stations_cache.update(key=provider, life_span=128, now=now)
            else:
                if holder.is_alive(now=now):
                    # cache not exists
                    return []
                # cache expired, wait for reloading
                holder.renewal(duration=128, now=now)
            # 2. check local storage
            value = self.__station_storage.all_stations(provider=provider)
            # 3. update memory cache
            self.__stations_cache.update(key=provider, value=value, life_span=600, now=now)
        # OK, return cached value
        return value

    # Override
    def add_station(self, identifier: Optional[ID], host: str, port: int, provider: ID, chosen: int = 0) -> bool:
        # 1. clear cache to reload
        self.__stations_cache.erase(key=provider)
        # 2. store into local storage
        return self.__station_storage.add_station(identifier=identifier, host=host, port=port,
                                                  provider=provider, chosen=chosen)

    # Override
    def update_station(self, identifier: Optional[ID], host: str, port: int, provider: ID, chosen: int = None) -> bool:
        # 1. clear cache to reload
        self.__stations_cache.erase(key=provider)
        # 2. store into local storage
        return self.__station_storage.update_station(identifier=identifier, host=host, port=port,
                                                     provider=provider, chosen=chosen)

    # Override
    def remove_station(self, host: str, port: int, provider: ID) -> bool:
        # 1. clear cache to reload
        self.__stations_cache.erase(key=provider)
        # 2. store into local storage
        return self.__station_storage.remove_station(host=host, port=port, provider=provider)

    # Override
    def remove_stations(self, provider: ID) -> bool:
        # 1. clear cache to reload
        self.__stations_cache.erase(key=provider)
        # 2. store into local storage
        return self.__station_storage.remove_stations(provider=provider)
