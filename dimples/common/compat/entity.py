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

from dimsdk import ID, Identifier
from dimsdk import ANYONE, EVERYONE, FOUNDER
from dimsdk import Address

from dimplugins import GeneralIdentifierFactory

from .network import network_to_type


class EntityID(Identifier):

    @property  # Override
    def type(self) -> int:
        network = self.address.type
        # compatible with MKM 0.9.*
        return network_to_type(network=network)


class EntityIDFactory(GeneralIdentifierFactory):

    # Override
    def _new_id(self, identifier: str, name: Optional[str], address: Address, terminal: Optional[str]):
        return EntityID(identifier=identifier, name=name, address=address, terminal=terminal)

    # Override
    def _parse(self, identifier: str) -> Optional[ID]:
        size = len(identifier)
        if size == 15 and identifier.lower() == 'anyone@anywhere':
            return ANYONE
        if size == 19 and identifier.lower() == 'everyone@everywhere':
            return EVERYONE
        if size == 13 and identifier.lower() == 'moky@anywhere':
            return FOUNDER
        return super()._parse(identifier=identifier)
