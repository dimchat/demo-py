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

from typing import Dict, Tuple, List

from dimsdk import ID

from ..common import SocketAddress
from ..common import ProviderDBI, StationDBI


class StationInfo:

    def __init__(self, remote: SocketAddress, provider: ID, chosen: int):
        super().__init__()
        self.remote = remote
        self.provider = provider
        self.chosen = chosen

    def __eq__(self, other) -> bool:
        if self is other:
            return True
        elif isinstance(other, StationInfo):
            return self.remote == other.remote
        else:
            return False

    def __ne__(self, other) -> bool:
        if self is other:
            return False
        elif isinstance(other, StationInfo):
            return self.remote != other.remote
        else:
            return True


class StationTable(ProviderDBI, StationDBI):
    """ Implementations of ProviderDBI """

    # noinspection PyUnusedLocal
    def __init__(self, root: str = None, public: str = None, private: str = None):
        super().__init__()
        self.__stations: Dict[ID, List[StationInfo]] = {}

    # noinspection PyMethodMayBeStatic
    def show_info(self):
        print('!!!       neighbors in memory only !!!')

    #
    #   Provider DBI
    #

    # Override
    def all_providers(self) -> List[Tuple[ID, int]]:
        gsp = ID.parse(identifier=ProviderDBI.GSP)
        return [(gsp, 1)]

    # Override
    def add_provider(self, provider: ID, chosen: int = 0) -> bool:
        pass

    # Override
    def update_provider(self, provider: ID, chosen: int) -> bool:
        pass

    # Override
    def remove_provider(self, provider: ID) -> bool:
        pass

    #
    #   Station DBI
    #

    # Override
    def all_stations(self, provider: ID) -> List[Tuple[SocketAddress, ID, int]]:
        stations = []
        array = self.__stations.get(provider)
        if array is not None:
            for item in array:
                info = (item.remote, item.provider, item.chosen)
                stations.append(info)
        return stations

    # Override
    def add_station(self, host: str, port: int, provider: ID, chosen: int = 0) -> bool:
        remote = (host, port)
        array = self.__stations.get(provider)
        if array is None:
            array = []
        else:
            for item in array:
                if item.remote == remote:
                    # station already exists
                    return False
        info = StationInfo(remote=remote, provider=provider, chosen=chosen)
        array.append(info)
        self.__stations[provider] = array
        return True

    # Override
    def update_station(self, host: str, port: int, provider: ID, chosen: int) -> bool:
        remote = (host, port)
        array = self.__stations.get(provider)
        if array is None:
            array = []
        else:
            for item in array:
                if item.remote == remote:
                    # station found
                    item.chosen = chosen
                    return True
        info = StationInfo(remote=remote, provider=provider, chosen=chosen)
        array.append(info)
        self.__stations[provider] = array
        return True

    # Override
    def remove_station(self, host: str, port: int, provider: ID) -> bool:
        remote = (host, port)
        array = self.__stations.get(provider)
        if array is not None:
            for item in array:
                if item.remote == remote:
                    # station found
                    array.remove(item)
                    return True

    # Override
    def remove_stations(self, provider: ID) -> bool:
        self.__stations.pop(provider, None)
        return True
