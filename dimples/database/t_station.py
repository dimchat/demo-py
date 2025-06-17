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

from ..utils import Config
from ..utils import SharedCacheManager
from ..common import ProviderInfo, StationInfo
from ..common import ProviderDBI, StationDBI

from .dos import StationStorage
from .redis import StationCache

from .t_base import DbTask


class SpTask(DbTask[str, List[ProviderInfo]]):

    def __init__(self, redis: StationCache, storage: StationStorage,
                 mutex_lock: threading.Lock, cache_pool: CachePool):
        super().__init__(mutex_lock=mutex_lock, cache_pool=cache_pool)
        self._redis = redis
        self._dos = storage

    @property  # Override
    def cache_key(self) -> str:
        return 'providers'

    # Override
    async def _read_data(self) -> Optional[List[ProviderInfo]]:
        # 1. the redis server will return None when cache not found
        # 2. when redis server return an empty array, no need to check local storage again
        array = await self._redis.load_providers()
        if array is not None:
            return array
        # 3. the local storage will return an empty array, when no provider
        array = await self._dos.all_providers()
        if array is None or len(array) == 0:
            # 4. return default provider then
            sp = ProviderInfo(identifier=ProviderInfo.GSP, chosen=0)
            array = [sp]  # placeholder
        # 5. update redis server
        await self._redis.save_providers(providers=array)
        return array

    # Override
    async def _write_data(self, value: List[ProviderInfo]) -> bool:
        return await self._redis.save_providers(providers=value)


class SrvTask(DbTask[ID, List[StationInfo]]):

    def __init__(self, provider: ID,
                 redis: StationCache, storage: StationStorage,
                 mutex_lock: threading.Lock, cache_pool: CachePool):
        super().__init__(mutex_lock=mutex_lock, cache_pool=cache_pool)
        self._provider = provider
        self._redis = redis
        self._dos = storage

    @property  # Override
    def cache_key(self) -> ID:
        return self._provider

    # Override
    async def _read_data(self) -> Optional[List[StationInfo]]:
        # 1. the redis server will return None when cache not found
        # 2. when redis server return an empty array, no need to check local storage again
        array = await self._redis.load_stations(provider=self._provider)
        if array is not None:
            return array
        # 3. the local storage will return an empty array, when no station for this sp
        array = await self._dos.all_stations(provider=self._provider)
        if array is None:
            # 4. return empty array as a placeholder for the memory cache
            array = []
        # 5. update redis server
        await self._redis.save_stations(stations=array, provider=self._provider)
        return array

    # Override
    async def _write_data(self, value: List[StationInfo]) -> bool:
        return await self._redis.save_stations(stations=value, provider=self._provider)


class StationTable(ProviderDBI, StationDBI):
    """ Implementations of ProviderDBI """

    def __init__(self, config: Config):
        super().__init__()
        man = SharedCacheManager()
        self._dim_cache = man.get_pool(name='dim')            # 'providers' => List[ProviderInfo]
        self._stations_cache = man.get_pool(name='stations')  # SP_ID => List[StationInfo]
        self._redis = StationCache(config=config)
        self._dos = StationStorage(config=config)
        self._lock = threading.Lock()

    def show_info(self):
        self._dos.show_info()

    def _new_sp_task(self) -> SpTask:
        return SpTask(redis=self._redis, storage=self._dos,
                      mutex_lock=self._lock, cache_pool=self._dim_cache)

    def _new_srv_task(self, provider: ID) -> SrvTask:
        return SrvTask(provider=provider,
                       redis=self._redis, storage=self._dos,
                       mutex_lock=self._lock, cache_pool=self._stations_cache)

    #
    #   Provider DBI
    #

    # Override
    async def all_providers(self) -> List[ProviderInfo]:
        task = self._new_sp_task()
        providers = await task.load()
        if providers is None:
            # should not happen
            providers = []
        return providers

    # Override
    async def add_provider(self, identifier: ID, chosen: int = 0) -> bool:
        with self._lock:
            # clear memory cache to reload
            self._dim_cache.erase(key='providers')
            # update redis & local storage
            ok1 = await self._redis.add_provider(identifier=identifier, chosen=chosen)
            ok2 = await self._dos.add_provider(identifier=identifier, chosen=chosen)
            return ok1 or ok2

    # Override
    async def update_provider(self, identifier: ID, chosen: int) -> bool:
        with self._lock:
            # clear memory cache to reload
            self._dim_cache.erase(key='providers')
            # update redis & local storage
            ok1 = await self._redis.update_provider(identifier=identifier, chosen=chosen)
            ok2 = await self._dos.update_provider(identifier=identifier, chosen=chosen)
            return ok1 or ok2

    # Override
    async def remove_provider(self, identifier: ID) -> bool:
        with self._lock:
            # clear memory cache to reload
            self._dim_cache.erase(key='providers')
            # update redis & local storage
            ok1 = await self._redis.remove_provider(identifier=identifier)
            ok2 = await self._dos.remove_provider(identifier=identifier)
            return ok1 or ok2

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
        with self._lock:
            # clear memory cache to reload
            self._stations_cache.erase(key=provider)
            # update redis & local storage
            ok1 = await self._redis.add_station(identifier=identifier, host=host, port=port,
                                                provider=provider, chosen=chosen)
            ok2 = await self._dos.add_station(identifier=identifier, host=host, port=port,
                                              provider=provider, chosen=chosen)
            return ok1 or ok2

    # Override
    async def update_station(self, identifier: Optional[ID], host: str, port: int,
                             provider: ID, chosen: int = None) -> bool:
        with self._lock:
            # clear memory cache to reload
            self._stations_cache.erase(key=provider)
            # update redis & local storage
            ok1 = await self._redis.update_station(identifier=identifier, host=host, port=port,
                                                   provider=provider, chosen=chosen)
            ok2 = await self._dos.update_station(identifier=identifier, host=host, port=port,
                                                 provider=provider, chosen=chosen)
            return ok1 or ok2

    # Override
    async def remove_station(self, host: str, port: int, provider: ID) -> bool:
        with self._lock:
            # clear memory cache to reload
            self._stations_cache.erase(key=provider)
            # update redis & local storage
            ok1 = await self._redis.remove_station(host=host, port=port, provider=provider)
            ok2 = await self._dos.remove_station(host=host, port=port, provider=provider)
            return ok1 or ok2

    # Override
    async def remove_stations(self, provider: ID) -> bool:
        with self._lock:
            # clear memory cache to reload
            self._stations_cache.erase(key=provider)
            # update redis & local storage
            ok1 = await self._redis.remove_stations(provider=provider)
            ok2 = await self._dos.remove_stations(provider=provider)
            return ok1 or ok2
