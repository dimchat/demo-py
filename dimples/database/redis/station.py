# -*- coding: utf-8 -*-
# ==============================================================================
# MIT License
#
# Copyright (c) 2021 Albert Moky
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

from dimsdk import ID

from ...utils import utf8_encode, utf8_decode, json_encode, json_decode
from ...common import ProviderInfo, StationInfo

from .base import RedisCache


class StationCache(RedisCache):

    # provider info cached in Redis will be removed after 30 minutes, after that
    # it should be reloaded from local storage
    EXPIRES = 1800  # seconds

    @property  # Override
    def db_name(self) -> Optional[str]:
        return 'dim'

    @property  # Override
    def tbl_name(self) -> str:
        return 'isp'

    """
        Service Providers
        ~~~~~~~~~~~~~~~~~

        redis key: 'dim.isp.providers'
    """
    def __providers_cache_name(self) -> str:
        return '%s.%s.providers' % (self.db_name, self.tbl_name)

    async def load_providers(self) -> Optional[List[ProviderInfo]]:
        """ get list of (SP_ID, chosen) """
        sp_key = self.__providers_cache_name()
        value = await self.get(name=sp_key)
        if value is None:
            return None
        js = utf8_decode(data=value)
        array = json_decode(string=js)
        return ProviderInfo.convert(array=array)

    async def save_providers(self, providers: List[ProviderInfo]) -> bool:
        sp_key = self.__providers_cache_name()
        array = ProviderInfo.revert(providers=providers)
        js = json_encode(obj=array)
        value = utf8_encode(string=js)
        return await self.set(name=sp_key, value=value, expires=self.EXPIRES)

    # Override
    async def all_providers(self) -> List[ProviderInfo]:
        providers = await self.load_providers()
        return [] if providers is None else providers

    # Override
    async def add_provider(self, identifier: ID, chosen: int = 0) -> bool:
        providers = await self.all_providers()
        for item in providers:
            if item.identifier == identifier:
                # already exist
                return True
        providers.insert(0, ProviderInfo(identifier=identifier, chosen=chosen))
        return await self.save_providers(providers=providers)

    # Override
    async def update_provider(self, identifier: ID, chosen: int) -> bool:
        providers = await self.all_providers()
        info = None
        for item in providers:
            if item.identifier == identifier:
                if item.chosen == chosen:
                    # not change
                    return True
                info = item
                break
        if info is None:
            info = ProviderInfo(identifier=identifier, chosen=chosen)
            providers.insert(0, info)
        else:
            info.chosen = chosen
        return await self.save_providers(providers=providers)

    # Override
    async def remove_provider(self, identifier: ID) -> bool:
        providers = await self.all_providers()
        info = None
        for item in providers:
            if item.identifier == identifier:
                info = item
                break
        if info is not None:
            providers.remove(info)
            return await self.save_providers(providers=providers)

    """
        Relay Stations
        ~~~~~~~~~~~~~~

        redis key: 'dim.isp.{ID}.stations'
    """
    def __stations_cache_name(self, provider: ID) -> str:
        return '%s.%s.%s.stations' % (self.db_name, self.tbl_name, provider)

    async def load_stations(self, provider: ID) -> Optional[List[StationInfo]]:
        """ get list of (host, port, SP_ID, chosen) """
        srv_key = self.__stations_cache_name(provider=provider)
        value = await self.get(name=srv_key)
        if value is None:
            return None
        js = utf8_decode(data=value)
        array = json_decode(string=js)
        return StationInfo.convert(array=array)

    async def save_stations(self, stations: List[StationInfo], provider: ID) -> bool:
        srv_key = self.__stations_cache_name(provider=provider)
        array = StationInfo.revert(stations=stations)
        js = json_encode(obj=array)
        value = utf8_encode(string=js)
        return await self.set(name=srv_key, value=value, expires=self.EXPIRES)

    # Override
    async def all_stations(self, provider: ID) -> List[StationInfo]:
        stations = await self.load_stations(provider=provider)
        return [] if stations is None else stations

    # Override
    async def add_station(self, identifier: Optional[ID], host: str, port: int, provider: ID, chosen: int = 0) -> bool:
        stations = await self.all_stations(provider=provider)
        for item in stations:
            if item.port == port and item.host == host:
                # already exists
                return True
        stations.insert(0, StationInfo(identifier=identifier, host=host, port=port, provider=provider, chosen=chosen))
        return await self.save_stations(stations=stations, provider=provider)

    # Override
    async def update_station(self, identifier: Optional[ID], host: str, port: int, provider: ID,
                             chosen: int = None) -> bool:
        stations = await self.all_stations(provider=provider)
        info = None
        for item in stations:
            if item.port == port and item.host == host:
                if item.chosen == chosen and item.identifier == identifier:
                    # not changed
                    return True
                info = item
                break
        if info is None:
            info = StationInfo(identifier=identifier, host=host, port=port, provider=provider, chosen=chosen)
            stations.insert(0, info)
        else:
            if not (identifier is None or identifier.is_broadcast):
                info.identifier = identifier
            info.chosen = chosen
        return await self.save_stations(stations=stations, provider=provider)

    # Override
    async def remove_station(self, host: str, port: int, provider: ID) -> bool:
        stations = await self.all_stations(provider=provider)
        info = None
        for item in stations:
            if item.port == port and item.host == host:
                info = item
                break
        if info is not None:
            stations.remove(info)
            return await self.save_stations(stations=stations, provider=provider)

    # Override
    async def remove_stations(self, provider: ID) -> bool:
        stations = await self.all_stations(provider=provider)
        if len(stations) == 0:
            # already empty
            return True
        return await self.save_stations(stations=[], provider=provider)
