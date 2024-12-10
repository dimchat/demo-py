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

from typing import Optional

from dimsdk import VerifyKey
from dimsdk import TransportableData
from dimsdk import Meta
from dimsdk import AccountFactoryManager
from dimplugins import DefaultMeta, BTCMeta, ETHMeta
from dimplugins import GeneralMetaFactory


class CompatibleMetaFactory(GeneralMetaFactory):

    def __init__(self, version: str):
        super().__init__(version=version)

    # Override
    def create_meta(self, public_key: VerifyKey, seed: Optional[str], fingerprint: Optional[TransportableData]) -> Meta:
        version = self.type
        if version == Meta.MKM:
            # MKM
            out = DefaultMeta(version='1', public_key=public_key, seed=seed, fingerprint=fingerprint)
        elif version == Meta.BTC:
            # BTC
            out = BTCMeta(version='2', public_key=public_key)
        elif version == Meta.ETH:
            # ETH
            out = ETHMeta(version='4', public_key=public_key)
        else:
            raise TypeError('unknown meta type: %d' % version)
        assert out.valid, 'meta error: %s' % out
        return out

    # Override
    def parse_meta(self, meta: dict) -> Optional[Meta]:
        gf = AccountFactoryManager.general_factory
        version = gf.get_meta_type(meta=meta, default='')
        if version == 'MKM' or version == 'mkm' or version == '1':
            # MKM
            out = DefaultMeta(meta=meta)
        elif version == 'BTC' or version == 'btc' or version == '2':
            # BTC
            out = BTCMeta(meta=meta)
        elif version == 'ETH' or version == 'eth' or version == '4':
            # ETH
            out = ETHMeta(meta=meta)
        else:
            raise TypeError('unknown meta type: %d' % version)
        if out.valid:
            return out
