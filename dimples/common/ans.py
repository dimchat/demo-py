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

from typing import Optional, List, Dict

from dimsdk import ID
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
        # reserved names
        reserved = {}  # str => boolean
        for keyword in self.KEYWORDS:
            reserved[keyword] = True
        self.__reserved = reserved
        # names map
        self.__names = {}  # ID => List[str]

    # Override
    def is_reserved(self, name: str) -> bool:
        return self.__reserved.get(name)

    # Override
    def identifier(self, name: str) -> Optional[ID]:
        """ Get ID by short name """
        return self.__caches.get(name)

    # Override
    def names(self, identifier: ID) -> List[str]:
        """ Get all short names with the same ID """
        array = self.__names.get(identifier)
        if array is None:
            array = []
            # TODO: update all tables?
            for name in self.__caches:
                if identifier == self.__caches[name]:
                    array.append(name)
            self.__names[identifier] = array
        return array

    # protected
    def cache(self, name: str, identifier: ID = None) -> bool:
        if self.is_reserved(name):
            # this name is reserved, cannot register
            return False
        if identifier is None:
            self.__caches.pop(name, None)
            # TODO: only remove one table?
            self.__names.clear()
        else:
            self.__caches[name] = identifier
            # names changed, remove the table of names for this ID
            self.__names.pop(identifier, None)
        return True

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

    def fix(self, records: Dict[str, str]) -> int:
        """ remove the keywords temporary before save new records """
        count = 0
        self.__reserved['assistant'] = False
        # self.__reserved['station'] = False
        for alias in records:
            identifier = ID.parse(identifier=records[alias])
            assert identifier is not None, 'record error: %s => %s' % (alias, records[alias])
            if self.save(name=alias, identifier=identifier):
                count += 1
        # self.__reserved['station'] = True
        self.__reserved['assistant'] = True
        return count
