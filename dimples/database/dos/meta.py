# -*- coding: utf-8 -*-
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

from mkm import ID, Meta

from .base import Storage
from .base import template_replace


class MetaStorage(Storage):
    """
        Meta for Entities (User/Group)
        ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
        file path: '.dim/public/{ADDRESS}/meta.js'
    """
    meta_path = '{PUBLIC}/{ADDRESS}/meta.js'

    def show_info(self):
        path = template_replace(self.meta_path, 'PUBLIC', self._public)
        print('!!!      meta path: %s' % path)

    def __meta_path(self, identifier: ID) -> str:
        path = self.meta_path
        path = template_replace(path, 'PUBLIC', self._public)
        return template_replace(path, 'ADDRESS', str(identifier.address))

    #
    #   MetaTable
    #
    def save_meta(self, meta: Meta, identifier: ID) -> bool:
        """ save meta into file """
        path = self.__meta_path(identifier=identifier)
        self.info('Saving meta into: %s' % path)
        return self.write_json(container=meta.dictionary, path=path)

    def meta(self, identifier: ID) -> Optional[Meta]:
        """ load meta from file """
        path = self.__meta_path(identifier=identifier)
        self.info('Loading meta from: %s' % path)
        info = self.read_json(path=path)
        if info is not None:
            return Meta.parse(meta=info)
