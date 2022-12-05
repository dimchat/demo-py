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

from typing import Dict, Set, Tuple

from dimsdk import ID

from ..common import OnlineDBI


class OnlineTable(OnlineDBI):
    """ Implementations of OnlineDBI """

    # noinspection PyUnusedLocal
    def __init__(self, root: str = None, public: str = None, private: str = None):
        super().__init__()
        self.__cache: Dict[ID, Set[Tuple[str, int]]] = {}  # ID => set(socket_address)

    # noinspection PyMethodMayBeStatic
    def show_info(self):
        print('!!!    online users in memory only !!!')

    #
    #   Online DBI
    #

    # Override
    def active_users(self) -> Set[ID]:
        users = set()
        all_users = set(self.__cache.keys())
        for uid in all_users:
            sockets = self.socket_addresses(identifier=uid)
            if len(sockets) > 0:
                users.add(uid)
        return users

    # Override
    def socket_addresses(self, identifier: ID) -> Set[Tuple[str, int]]:
        sockets = self.__cache.get(identifier)
        return set() if sockets is None else sockets

    # Override
    def add_socket_address(self, identifier: ID, address: Tuple[str, int]) -> Set[Tuple[str, int]]:
        sockets = self.socket_addresses(identifier=identifier)
        sockets.add(address)
        self.__cache[identifier] = sockets
        return sockets

    # Override
    def remove_socket_address(self, identifier: ID, address: Tuple[str, int]) -> Set[Tuple[str, int]]:
        sockets = self.socket_addresses(identifier=identifier)
        sockets.discard(address)
        if len(sockets) > 0:
            self.__cache[identifier] = sockets
        else:
            self.__cache.pop(identifier, None)
        return sockets
