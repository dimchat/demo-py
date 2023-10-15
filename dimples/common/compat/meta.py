# -*- coding: utf-8 -*-
#
#   Ming-Ke-Ming : Decentralized User Identity Authentication
#
#                                Written in 2020 by Moky <albert.moky@gmail.com>
#
# ==============================================================================
# MIT License
#
# Copyright (c) 2020 Albert Moky
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

from typing import Optional, Union, Any, Dict

from dimsdk import VerifyKey, SignKey, PrivateKey
from dimsdk import TransportableData
from dimsdk import Address
from dimsdk import MetaType, Meta, MetaFactory, BaseMeta
from dimsdk import AccountFactoryManager

from ...utils import utf8_encode
from .btc import BTCAddress


"""
    Default Meta to build ID with 'name@address'
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    version:
        0x01 - MKM

    algorithm:
        CT      = fingerprint = sKey.sign(seed);
        hash    = ripemd160(sha256(CT));
        code    = sha256(sha256(network + hash)).prefix(4);
        address = base58_encode(network + hash + code);
"""


class CompatibleDefaultMeta(BaseMeta):

    def __init__(self, meta: Dict[str, Any] = None,
                 version: int = None, key: VerifyKey = None,
                 seed: Optional[str] = None, fingerprint: Optional[TransportableData] = None):
        super().__init__(meta=meta, version=version, key=key, seed=seed, fingerprint=fingerprint)
        # caches
        self.__addresses = {}

    # Override
    def generate_address(self, network: int = None) -> Address:
        assert self.type == MetaType.MKM, 'meta version error: %d' % self.type
        # check caches
        address = self.__addresses.get(network)
        if address is None:
            # generate and cache it
            data = self.fingerprint
            address = BTCAddress.from_data(data, network=network)
            self.__addresses[network] = address
        return address


"""
    Meta to build BTC address for ID
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    version:
        0x02 - BTC
        0x03 - ExBTC

    algorithm:
        CT      = key.data;
        hash    = ripemd160(sha256(CT));
        code    = sha256(sha256(network + hash)).prefix(4);
        address = base58_encode(network + hash + code);
"""


class CompatibleBTCMeta(BaseMeta):

    def __init__(self, meta: Dict[str, Any] = None,
                 version: int = None, key: VerifyKey = None,
                 seed: Optional[str] = None, fingerprint: Optional[TransportableData] = None):
        super().__init__(meta=meta, version=version, key=key, seed=seed, fingerprint=fingerprint)
        # caches
        self.__address: Optional[Address] = None

    # Override
    def generate_address(self, network: int = None) -> Address:
        assert self.type in [MetaType.BTC, MetaType.ExBTC], 'meta version error: %d' % self.type
        # assert network == NetworkType.BTC_MAIN, 'BTC address type error: %d' % network
        if self.__address is None:
            # TODO: compress public key?
            key = self.public_key
            data = key.data
            # generate and cache it
            self.__address = BTCAddress.from_data(data, network=network)
        return self.__address


class CompatibleMetaFactory(MetaFactory):

    def __init__(self, version: Union[int, MetaType]):
        super().__init__()
        if isinstance(version, MetaType):
            version = version.value
        self.__type = version

    # Override
    def generate_meta(self, key: SignKey, seed: Optional[str]) -> Meta:
        if seed is None or len(seed) == 0:
            fingerprint = None
        else:
            sig = key.sign(data=utf8_encode(string=seed))
            fingerprint = TransportableData.create(data=sig)
        assert isinstance(key, PrivateKey), 'private key error: %s' % key
        public_key = key.public_key
        return self.create_meta(key=public_key, seed=seed, fingerprint=fingerprint)

    # Override
    def create_meta(self, key: VerifyKey, seed: Optional[str], fingerprint: Optional[TransportableData]) -> Meta:
        if self.__type == MetaType.MKM:
            # MKM
            return CompatibleDefaultMeta(version=self.__type, key=key, seed=seed, fingerprint=fingerprint)
        elif self.__type == MetaType.BTC:
            # BTC
            return CompatibleBTCMeta(version=self.__type, key=key)
        elif self.__type == MetaType.ExBTC:
            # ExBTC
            return CompatibleBTCMeta(version=self.__type, key=key, seed=seed, fingerprint=fingerprint)

    # Override
    def parse_meta(self, meta: dict) -> Optional[Meta]:
        gf = AccountFactoryManager.general_factory
        version = gf.get_meta_type(meta=meta, default=0)
        if version == MetaType.MKM:
            # MKM
            out = CompatibleDefaultMeta(meta=meta)
        elif version == MetaType.BTC or version == MetaType.ExBTC:
            # BTC, ExBTC
            out = CompatibleBTCMeta(meta=meta)
        else:
            raise TypeError('unknown meta type: %d' % version)
        if out.valid:
            return out
