# -*- coding: utf-8 -*-
# ==============================================================================
# MIT License
#
# Copyright (c) 2019 Albert Moky
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

"""
    Address Name Service
    ~~~~~~~~~~~~~~~~~~~~

    A map for short name to ID, just like DNS
"""

from typing import Optional, List, Set, Tuple

from dimsdk import IDFactory
from dimsdk import ID, Address
from dimsdk import ANYONE, EVERYONE, FOUNDER
from dimsdk import AddressNameService


class AddressNameServer(AddressNameService):

    def __init__(self):
        super().__init__()
        # ANS records
        self.__caches = {
            'all': EVERYONE,
            'everyone': EVERYONE,
            'anyone': ANYONE,
            'owner': ANYONE,
            'founder': FOUNDER,
        }

    # Override
    def is_reserved(self, name: str) -> bool:
        return name in self.KEYWORDS

    # Override
    def identifier(self, name: str) -> Optional[ID]:
        """ Get ID by short name """
        return self.__caches.get(name)

    # Override
    def names(self, identifier: ID) -> List[str]:
        """ Get all short names with the same ID """
        array = []
        for (key, value) in self.__caches.items():
            if key == identifier:
                array.append(value)
        return array

    def cache(self, name: str, identifier: ID = None) -> bool:
        if self.is_reserved(name):
            # this name is reserved, cannot register
            return False
        if identifier is None:
            self.__caches.pop(name, None)
        else:
            self.__caches[name] = identifier
        return True

    def load(self):
        # TODO: load all ANS records from database
        pass

    def save(self, name: str, identifier: ID = None) -> bool:
        """
        Save ANS record

        :param name:       username
        :param identifier: user ID; if empty, means delete this name
        :return: True on success
        """
        if self.cache(name=name, identifier=identifier):
            # TODO: save new record into database
            return True

    def fix(self, fixed: Set[Tuple[str, ID]]):
        """ remove the keywords temporary before save new redords """
        self.KEYWORDS.remove('assistant')
        # self.KEYWORDS.remove('station')
        for item in fixed:
            self.save(name=item[0], identifier=item[1])
        # self.KEYWORDS.append('station')
        self.KEYWORDS.append('assistant')


class ANSFactory(IDFactory):

    def __init__(self, factory: IDFactory, ans: AddressNameService):
        super().__init__()
        self.__origin = factory
        self.__ans = ans

    # Override
    def generate_identifier(self, meta, network: int, terminal: Optional[str]) -> ID:
        return self.__origin.generate_identifier(meta=meta, network=network, terminal=terminal)

    # Override
    def create_identifier(self, name: Optional[str], address: Address, terminal: Optional[str]) -> ID:
        return self.__origin.create_identifier(address=address, name=name, terminal=terminal)

    # Override
    def parse_identifier(self, identifier: str) -> Optional[ID]:
        # try ANS record
        aid = self.__ans.identifier(name=identifier)
        if aid is None:
            # parse by original factory
            aid = self.__origin.parse_identifier(identifier=identifier)
        return aid
