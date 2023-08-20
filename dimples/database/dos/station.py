# -*- coding: utf-8 -*-
# ==============================================================================
# MIT License
#
# Copyright (c) 2023 Albert Moky
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

from ...common import ProviderInfo, StationInfo
from ...common import ProviderDBI, StationDBI

from .base import Storage
from .base import template_replace


class StationStorage(Storage, ProviderDBI, StationDBI):
    """
        Station Storage
        ~~~~~~~~~~~~~~~
        file path: '.dim/public/providers.js'
        file path: '.dim/public/{ADDRESS}/stations.js'
    """

    providers_path = '{PUBLIC}/providers.js'
    stations_path = '{PUBLIC}/{ADDRESS}/stations.js'

    def show_info(self):
        path1 = template_replace(self.providers_path, 'PUBLIC', self._public)
        path2 = template_replace(self.stations_path, 'PUBLIC', self._public)
        print('!!!      providers path: %s' % path1)
        print('!!!       stations path: %s' % path2)

    def __providers_path(self) -> str:
        path = self.providers_path
        return template_replace(path, 'PUBLIC', self._public)

    def __stations_path(self, provider: ID) -> str:
        path = self.stations_path
        path = template_replace(path, 'PUBLIC', self._public)
        return template_replace(path, 'ADDRESS', str(provider.address))

    #
    #   Provider DBI
    #

    # Override
    def all_providers(self) -> List[ProviderInfo]:
        """ load providers from file """
        path = self.__providers_path()
        self.info(msg='Loading providers from: %s' % path)
        providers = self.read_json(path=path)
        if providers is None:
            # service providers not found
            return []
        return ProviderInfo.convert(array=providers)

    def _save_providers(self, providers: List[ProviderInfo]) -> bool:
        """ save providers into file """
        path = self.__providers_path()
        self.info(msg='Saving providers into: %s' % path)
        return self.write_json(container=ProviderInfo.revert(array=providers), path=path)

    # Override
    def add_provider(self, identifier: ID, chosen: int = 0) -> bool:
        """ add provider with chosen order """
        providers = self.all_providers()
        for item in providers:
            if item.identifier == identifier:
                self.warning(msg='provider exists: %s, %s' % (identifier, providers))
                return True
        providers.insert(0, ProviderInfo(identifier=identifier, chosen=chosen))
        return self._save_providers(providers=providers)

    # Override
    def update_provider(self, identifier: ID, chosen: int) -> bool:
        """ update provider with chosen order """
        providers = self.all_providers()
        info = None
        for item in providers:
            if item.identifier == identifier:
                if item.chosen == chosen:
                    self.warning(msg='provider not change: %s, %d' % (identifier, chosen))
                    return True
                info = item
                break
        if info is None:
            info = ProviderInfo(identifier=identifier, chosen=chosen)
            providers.insert(0, info)
        else:
            info.chosen = chosen
        return self._save_providers(providers=providers)

    # Override
    def remove_provider(self, identifier: ID) -> bool:
        """ remove provider with SP ID """
        providers = self.all_providers()
        info = None
        for item in providers:
            if item.identifier == identifier:
                info = item
                break
        if info is not None:
            providers.remove(info)
            return self._save_providers(providers=providers)

    #
    #   Station DBI
    #

    # Override
    def all_stations(self, provider: ID) -> List[StationInfo]:
        """ load stations with SP ID """
        path = self.__stations_path(provider=provider)
        self.info(msg='Loading stations from: %s' % path)
        stations = self.read_json(path=path)
        if stations is None:
            # stations not found
            return []
        return StationInfo.convert(array=stations)

    def _save_stations(self, stations: List[StationInfo], provider: ID) -> bool:
        """ save stations into file """
        path = self.__stations_path(provider=provider)
        self.info(msg='Saving stations into: %s' % path)
        return self.write_json(container=StationInfo.revert(array=stations), path=path)

    # Override
    def add_station(self, identifier: Optional[ID], host: str, port: int, provider: ID, chosen: int = 0) -> bool:
        """ add station with chosen order """
        stations = self.all_stations(provider=provider)
        for item in stations:
            if item.port == port and item.host == host:
                self.warning(msg='station exists: %s, %d, %s' % (host, port, stations))
                return True
        stations.insert(0, StationInfo(identifier=identifier, host=host, port=port, provider=provider, chosen=chosen))
        return self._save_stations(stations=stations, provider=provider)

    # Override
    def update_station(self, identifier: Optional[ID], host: str, port: int, provider: ID, chosen: int = None) -> bool:
        """ update station with SP ID """
        stations = self.all_stations(provider=provider)
        info = None
        for item in stations:
            if item.port == port and item.host == host:
                if item.chosen == chosen and item.identifier == identifier:
                    self.warning(msg='station not change: %s, %d' % (host, port))
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
        return self._save_stations(stations=stations, provider=provider)

    # Override
    def remove_station(self, host: str, port: int, provider: ID) -> bool:
        """ remove station with SP ID """
        stations = self.all_stations(provider=provider)
        info = None
        for item in stations:
            if item.port == port and item.host == host:
                info = item
                break
        if info is not None:
            stations.remove(info)
            return self._save_stations(stations=stations, provider=provider)

    # Override
    def remove_stations(self, provider: ID) -> bool:
        """ remove all stations with SP ID """
        stations = self.all_stations(provider=provider)
        if len(stations) == 0:
            # already empty
            return True
        return self._save_stations(stations=[], provider=provider)
