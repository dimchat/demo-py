# -*- coding: utf-8 -*-
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

from dimsdk import IDFactory
from dimsdk import ID, Address
from dimplugins import PluginLoader

from ...common.compat import EntityIDFactory
from ...common import CommonLoader, CommonPluginLoader

from ..facebook import ClientFacebook


class ClientLoader(CommonLoader):
    """ Extensions Loader """

    # Override
    def _create_plugin_loader(self) -> PluginLoader:
        return ClientPluginLoader()


class ClientPluginLoader(CommonPluginLoader):

    # Override
    def _register_id_factory(self):
        ID.set_factory(factory=AnsIdentifierFactory())


_identifier_factory = EntityIDFactory()


class AnsIdentifierFactory(IDFactory):

    # Override
    def generate_identifier(self, meta, network: Optional[int], terminal: Optional[str]) -> ID:
        return _identifier_factory.generate_identifier(meta=meta, network=network, terminal=terminal)

    # Override
    def create_identifier(self, name: Optional[str], address: Address, terminal: Optional[str]) -> ID:
        return _identifier_factory.create_identifier(name=name, address=address, terminal=terminal)

    # Override
    def parse_identifier(self, identifier: str) -> Optional[ID]:
        # try ANS record
        ans = ClientFacebook.ans
        if ans is not None:
            cid = ans.identifier(name=identifier)
            if cid is not None:
                return cid
        # parse by original factory
        return _identifier_factory.parse_identifier(identifier=identifier)
