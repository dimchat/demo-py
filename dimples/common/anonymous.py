# -*- coding: utf-8 -*-
#
#   DIM-SDK : Decentralized Instant Messaging Software Development Kit
#
#                                Written in 2023 by Moky <albert.moky@gmail.com>
#
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

from dimsdk import EntityType, Address, ID
from dimplugins import BTCAddress, ETHAddress

from ..utils import hex_decode, base58_decode


class Anonymous:

    @classmethod
    def get_name(cls, identifier: ID) -> str:
        name = identifier.name
        if name is None or len(name) == 0:
            name = entity_name(network=identifier.type)
        string = cls.number_string(address=identifier.address)
        return '%s (%s)' % (name, string)

    @classmethod
    def number_string(cls, address: Address) -> str:
        number = cls.get_number(address=address)
        string = str(number).zfill(10)
        a = string[0:3]
        b = string[3:6]
        c = string[6:]
        return '%s-%s-%s' % (a, b, c)

    @classmethod
    def get_number(cls, address: Address) -> int:
        if isinstance(address, BTCAddress):
            return btc_number(address=str(address))
        elif isinstance(address, ETHAddress):
            return eth_number(address=str(address))
        # TODO: other chain?
        return 0
        # assert False, 'address error: %s' % address


def entity_name(network: int) -> str:
    """ get name for entity type """
    if network == EntityType.BOT:
        return 'Bot'
    elif network == EntityType.STATION:
        return 'Station'
    elif network == EntityType.ISP:
        return 'ISP'
    elif network == EntityType.ICP:
        return 'ICP'
    elif EntityType.is_user(network=network):
        return 'User'
    elif EntityType.is_group(network=network):
        return 'Group'
    assert False, 'unknown entity type: %d' % network


def btc_number(address: str) -> int:
    data = base58_decode(string=address)
    return 0 if data is None else user_number(data)


def eth_number(address: str) -> int:
    data = hex_decode(string=address[2:])
    return 0 if data is None else user_number(data)


def user_number(cc: bytes) -> int:
    size = len(cc)
    return (cc[size-4] & 0xFF) << 24 | \
           (cc[size-3] & 0xFF) << 16 | \
           (cc[size-2] & 0xFF) << 8 | \
           (cc[size-1] & 0xFF)
