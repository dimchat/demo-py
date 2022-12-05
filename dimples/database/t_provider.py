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

from typing import Optional, Set, Dict, Tuple

from dimsdk import ID
from dimsdk import Station

from ..common import ProviderDBI


class ProviderTable(ProviderDBI):
    """ Implementations of ProviderDBI """

    # noinspection PyUnusedLocal
    def __init__(self, root: str = None, public: str = None, private: str = None):
        super().__init__()
        self.__neighbors: Dict[Tuple[str, int], ID] = {}

    # noinspection PyMethodMayBeStatic
    def show_info(self):
        print('!!!       neighbors in memory only !!!')

    #
    #   Provider DBI
    #

    # Override
    def all_neighbors(self) -> Set[Tuple[str, int, Optional[ID]]]:
        neighbors = set()
        addresses = set(self.__neighbors.keys())
        for remote in addresses:
            identifier = self.__neighbors.get(remote)
            info = (remote[0], remote[1], identifier)
            neighbors.add(info)
        return neighbors

    # Override
    def get_neighbor(self, host: str, port: int) -> Optional[ID]:
        remote = (host, port)
        return self.__neighbors.get(remote)

    # Override
    def add_neighbor(self, host: str, port: int, identifier: ID = None) -> bool:
        remote = (host, port)
        if identifier is None:
            identifier = Station.ANY
        self.__neighbors[remote] = identifier
        return True

    # Override
    def del_neighbor(self, host: str, port: int) -> Optional[ID]:
        remote = (host, port)
        identifier = self.__neighbors.get(remote)
        self.__neighbors.pop(remote, None)
        return identifier
