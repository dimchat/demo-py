# -*- coding: utf-8 -*-
#
#   Ming-Ke-Ming : Decentralized User Identity Authentication
#
#                                Written in 2019 by Moky <albert.moky@gmail.com>
#
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

from enum import IntEnum
from typing import Any

from ...utils import Log


class MetaVersion(IntEnum):
    """
        @enum MKMMetaVersion

        @abstract Defined for meta data structure to generate identifier.

        @discussion Generate & check ID/Address

            MKMMetaVersion_MKM give a seed string first, and sign this seed to get
            fingerprint; after that, use the fingerprint to generate address.
            This will get a firmly relationship between (username, address & key).

            MKMMetaVersion_BTC use the key data to generate address directly.
            This can build a BTC address for the entity ID without username.

            MKMMetaVersion_ExBTC use the key data to generate address directly, and
            sign the seed to get fingerprint (just for binding username & key).
            This can build an entity ID with username and BTC address.

        Bits:
            0000 0001 - this meta contains seed as ID.name
            0000 0010 - this meta generate BTC address
            0000 0100 - this meta generate ETH address
            ...
    """
    DEFAULT = 0x01
    MKM = 0x01    # 0000 0001: username@address

    BTC = 0x02    # 0000 0010: btc_address
    ExBTC = 0x03  # 0000 0011: username@btc_address

    ETH = 0x04    # 0000 0100: eth_address
    ExETH = 0x05  # 0000 0101: username@eth_address

    @classmethod
    def parse_str(cls, version: Any) -> str:
        if isinstance(version, str):
            return version
        elif isinstance(version, MetaVersion):
            version = version.value
        return str(version)

    @classmethod
    def has_seed(cls, version: Any) -> bool:
        version = cls.parse_int(version=version, default=0)
        return 0 < version and (version & cls.MKM) == cls.MKM

    @classmethod
    def parse_int(cls, version: Any, default: int) -> int:
        if version is None:
            return default
        elif isinstance(version, int):
            # exactly
            return version
        elif isinstance(version, bool) or isinstance(version, float):
            return int(version)
        elif isinstance(version, str):
            # fixed values
            if version == 'MKM' or version == 'mkm':
                return cls.MKM.value
            elif version == 'BTC' or version == 'btc':
                return cls.BTC.value
            elif version == 'ExBTC':
                return cls.ExBTC.value
            elif version == 'ETH' or version == 'eth':
                return cls.ETH.value
            elif version == 'ExETH':
                return cls.ExETH.value
            # TODO: other algorithms
        elif isinstance(version, MetaVersion):
            # enum
            return version.value
        else:
            return -1
        try:
            return int(version)
        except Exception as error:
            Log.error(msg='meta type error: %s, %s' % (version, error))
            return -1
