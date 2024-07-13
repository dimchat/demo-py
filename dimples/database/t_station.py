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

import threading
from typing import Optional, List

from aiou.mem import CachePool

from dimsdk import ID

from ..utils import SharedCacheManager
from ..common import ProviderInfo, StationInfo
from ..common import ProviderDBI, StationDBI

from .dos import StationStorage
from .redis import StationCache

from .t_base import DbInfo, DbTask


class SpTask(DbTask):

    MEM_CACHE_EXPIRES = 300  # seconds
    MEM_CACHE_REFRESH = 32   # seconds

    def __init__(self,
                 cache_pool: CachePool, redis: StationCache, storage: StationStorage,
                 mutex_lock: threading.Lock):
        super().__init__(cache_pool=cache_pool,
                         cache_expires=self.MEM_CACHE_EXPIRES,
                         cache_refresh=self.MEM_CACHE_REFRESH,
                         mutex_lock=mutex_lock)
        self._redis = redis
        self._dos = storage

    # Override
    def cache_key(self) -> str:
        return 'providers'

    # Override
    async def _load_redis_cache(self) -> Optional[List[ProviderInfo]]:
        array = await self._redis.all_providers()
        if array is None or len(array) == 0:
            return None
        else:
            return array

    # Override
    async def _save_redis_cache(self, value: List[ProviderInfo]) -> bool:
        return await self._redis.save_providers(providers=value)

    # Override
    async def _load_local_storage(self) -> Optional[List[ProviderInfo]]:
        array = await self._dos.all_providers()
        if array is None or len(array) == 0:
            return None
        else:
            return array

    # Override
    async def _save_local_storage(self, value: List[ProviderInfo]) -> bool:
        pass


class SrvTask(DbTask):

    MEM_CACHE_EXPIRES = 300  # seconds
    MEM_CACHE_REFRESH = 32   # seconds

    def __init__(self, provider: ID,
                 cache_pool: CachePool, redis: StationCache, storage: StationStorage,
                 mutex_lock: threading.Lock):
        super().__init__(cache_pool=cache_pool,
                         cache_expires=self.MEM_CACHE_EXPIRES,
                         cache_refresh=self.MEM_CACHE_REFRESH,
                         mutex_lock=mutex_lock)
        self._provider = provider
        self._redis = redis
        self._dos = storage

    # Override
    def cache_key(self) -> ID:
        return self._provider

    # Override
    async def _load_redis_cache(self) -> Optional[List[StationInfo]]:
        array = await self._redis.all_stations(provider=self._provider)
        if array is None or len(array) == 0:
            return None
        else:
            return array

    # Override
    async def _save_redis_cache(self, value: List[StationInfo]) -> bool:
        return await self._redis.save_stations(stations=value, provider=self._provider)

    # Override
    async def _load_local_storage(self) -> Optional[List[StationInfo]]:
        array = await self._dos.all_stations(provider=self._provider)
        if array is None or len(array) == 0:
            return None
        else:
            return array

    # Override
    async def _save_local_storage(self, value: List[StationInfo]) -> bool:
        pass


class StationTable(ProviderDBI, StationDBI):
    """ Implementations of ProviderDBI """

    def __init__(self, info: DbInfo):
        super().__init__()
        man = SharedCacheManager()
        self.__dim_cache = man.get_pool(name='dim')            # 'providers' => List[ProviderInfo]
        self.__stations_cache = man.get_pool(name='stations')  # SP_ID => List[StationInfo]
        self.__redis = StationCache(connector=info.redis_connector)
        self.__dos = StationStorage(root=info.root_dir, public=info.public_dir, private=info.private_dir)
        self.__lock = threading.Lock()

    def show_info(self):
        self.__dos.show_info()

    def _new_sp_task(self) -> SpTask:
        return SpTask(cache_pool=self.__dim_cache, redis=self.__redis, storage=self.__dos,
                      mutex_lock=self.__lock)

    def _new_srv_task(self, provider: ID) -> SrvTask:
        return SrvTask(provider=provider,
                       cache_pool=self.__stations_cache, redis=self.__redis, storage=self.__dos,
                       mutex_lock=self.__lock)

    #
    #   Provider DBI
    #

    # Override
    async def all_providers(self) -> List[ProviderInfo]:
        task = self._new_sp_task()
        providers = await task.load()
        if providers is None or len(providers) == 0:
            providers = [ProviderInfo(identifier=ProviderInfo.GSP, chosen=0)]
            self.__dim_cache.update(key='providers', value=providers, life_span=SpTask.MEM_CACHE_EXPIRES)
        return providers

    # Override
    async def add_provider(self, identifier: ID, chosen: int = 0) -> bool:
        with self.__lock:
            # 1. clear cache to reload
            self.__dim_cache.erase(key='providers')
            # 2. store into local storage
            return await self.__dos.add_provider(identifier=identifier, chosen=chosen)

    # Override
    async def update_provider(self, identifier: ID, chosen: int) -> bool:
        with self.__lock:
            # 1. clear cache to reload
            self.__dim_cache.erase(key='providers')
            # 2. store into local storage
            return await self.__dos.update_provider(identifier=identifier, chosen=chosen)

    # Override
    async def remove_provider(self, identifier: ID) -> bool:
        with self.__lock:
            # 1. clear cache to reload
            self.__dim_cache.erase(key='providers')
            # 2. store into local storage
            return await self.__dos.remove_provider(identifier=identifier)

    #
    #   Station DBI
    #

    # Override
    async def all_stations(self, provider: ID) -> List[StationInfo]:
        task = self._new_srv_task(provider=provider)
        stations = await task.load()
        return [] if stations is None else stations

    # Override
    async def add_station(self, identifier: Optional[ID], host: str, port: int,
                          provider: ID, chosen: int = 0) -> bool:
        with self.__lock:
            # 1. clear cache to reload
            self.__stations_cache.erase(key=provider)
            # 2. store into local storage
            return await self.__dos.add_station(identifier=identifier, host=host, port=port,
                                                provider=provider, chosen=chosen)

    # Override
    async def update_station(self, identifier: Optional[ID], host: str, port: int,
                             provider: ID, chosen: int = None) -> bool:
        with self.__lock:
            # 1. clear cache to reload
            self.__stations_cache.erase(key=provider)
            # 2. store into local storage
            return await self.__dos.update_station(identifier=identifier, host=host, port=port,
                                                   provider=provider, chosen=chosen)

    # Override
    async def remove_station(self, host: str, port: int, provider: ID) -> bool:
        with self.__lock:
            # 1. clear cache to reload
            self.__stations_cache.erase(key=provider)
            # 2. store into local storage
            return await self.__dos.remove_station(host=host, port=port, provider=provider)

    # Override
    async def remove_stations(self, provider: ID) -> bool:
        with self.__lock:
            # 1. clear cache to reload
            self.__stations_cache.erase(key=provider)
            # 2. store into local storage
            return await self.__dos.remove_stations(provider=provider)
