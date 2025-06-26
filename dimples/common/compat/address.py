# -*- coding: utf-8 -*-
#
#   Ming-Ke-Ming : Decentralized User Identity Authentication
#
#                                Written in 2024 by Moky <albert.moky@gmail.com>
#
# ==============================================================================
# MIT License
#
# Copyright (c) 2024 Albert Moky
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

from dimsdk import ConstantString
from dimsdk import EntityType
from dimsdk import Address, ANYWHERE, EVERYWHERE
from dimplugins import BTCAddress, ETHAddress
from dimplugins import BaseAddressFactory

from ...utils.thanos import thanos


class CompatibleAddressFactory(BaseAddressFactory):

    def reduce_memory(self) -> int:
        """
        Call it when received 'UIApplicationDidReceiveMemoryWarningNotification',
        this will remove 50% of cached objects

        :return: number of survivors
        """
        finger = 0
        finger = thanos(self._addresses, finger)
        return finger >> 1

    # Override
    def _parse(self, address: str) -> Optional[Address]:
        size = len(address)
        if size == 0:
            assert False, 'address should not be empty'
        elif size == 8:
            # "anywhere"
            if address.lower() == 'anywhere':
                return ANYWHERE
        elif size == 10:
            # "everywhere"
            if address.lower() == 'everywhere':
                return EVERYWHERE
        #
        #  checking normal address
        #
        if 26 <= size <= 35:
            res = BTCAddress.from_str(address=address)
        elif size == 42:
            res = ETHAddress.from_str(address=address)
        else:
            # assert False, 'invalid address: %s' % address
            res = None
        #
        #  TODO: other types of address
        #
        if res is None and 4 <= size <= 64:
            res = UnknownAddress(address=address)
        assert res is not None, 'invalid address: %s' % address
        return res


class UnknownAddress(ConstantString, Address):
    """
        Unsupported Address
        ~~~~~~~~~~~~~~~~~~~
    """

    def __init__(self, address: str):
        super().__init__(string=address)

    @property  # Override
    def network(self) -> int:
        return EntityType.USER.value
