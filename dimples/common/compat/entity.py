# -*- coding: utf-8 -*-
#
#   Ming-Ke-Ming : Decentralized User Identity Authentication
#
#                                Written in 2022 by Moky <albert.moky@gmail.com>
#
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

from typing import Optional

from dimsdk.core import thanos
from dimsdk import EntityType
from dimsdk import ID, Identifier
from dimsdk import ANYONE, EVERYONE, FOUNDER
from dimsdk import Address

from dimplugins import GeneralIdentifierFactory

from .network import network_to_type


class EntityIDFactory(GeneralIdentifierFactory):

    def reduce_memory(self) -> int:
        """
        Call it when received 'UIApplicationDidReceiveMemoryWarningNotification',
        this will remove 50% of cached objects

        :return: number of survivors
        """
        finger = 0
        finger = thanos(self._identifiers, finger)
        return finger >> 1

    # Override
    def _new_id(self, identifier: str, name: Optional[str], address: Address, terminal: Optional[str]):
        # override for customized ID
        return EntityID(identifier=identifier, name=name, address=address, terminal=terminal)

    # Override
    def _parse(self, identifier: str) -> Optional[ID]:
        size = 0 if identifier is None else len(identifier)
        if size < 4 or size > 64:
            assert False, 'ID error: %s' % identifier
        elif size == 15:
            # "anyone@anywhere"
            if identifier.lower() == 'anyone@anywhere':
                return ANYONE
        elif size == 19:
            # "everyone@everywhere"
            # "stations@everywhere"
            if identifier.lower() == 'everyone@everywhere':
                return EVERYONE
        elif size == 13:
            # "moky@anywhere"
            if identifier.lower() == 'moky@anywhere':
                return FOUNDER
        # normal ID
        return super()._parse(identifier=identifier)


class EntityID(Identifier):

    @property  # Override
    def type(self) -> int:
        name = self.name
        if name is None or len(name) == 0:
            # all ID without 'name' field must be a user
            # e.g.: BTC address
            return EntityType.USER.value
        # compatible with MKM 0.9.*
        address = self.address
        return network_to_type(network=address.network)
