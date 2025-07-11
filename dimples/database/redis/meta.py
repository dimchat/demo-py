# -*- coding: utf-8 -*-
# ==============================================================================
# MIT License
#
# Copyright (c) 2021 Albert Moky
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

from dimsdk import ID, Meta

from ...utils import json_encode, json_decode, utf8_encode, utf8_decode
from ...utils import Logging
from ...common.compat import Compatible

from .base import RedisCache


class MetaCache(RedisCache, Logging):

    # meta cached in Redis will be removed after 10 hours, after that
    # it will be reloaded from local storage if it's still need.
    EXPIRES = 36000  # seconds

    @property  # Override
    def db_name(self) -> Optional[str]:
        return 'mkm'

    @property  # Override
    def tbl_name(self) -> str:
        return 'meta'

    """
        Meta key for Entities (User/Group)
        ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

        redis key: 'mkm.meta.{ID}'
    """
    def __cache_name(self, identifier: ID) -> str:
        return '%s.%s.%s' % (self.db_name, self.tbl_name, identifier)

    async def get_meta(self, identifier: ID) -> Optional[Meta]:
        key = self.__cache_name(identifier=identifier)
        value = await self.get(name=key)
        if value is None:
            # cache not found
            return None
        else:
            js = utf8_decode(data=value)
            assert js is not None, 'failed to decode string: %s' % value
            info = json_decode(string=js)
            assert info is not None, 'meta error: %s' % value
            Compatible.fix_meta_version(meta=info)
        try:
            return Meta.parse(meta=info)
        except Exception as error:
            self.error(msg='meta error: %s, %s' % (error, info))

    async def save_meta(self, meta: Meta, identifier: ID) -> bool:
        dictionary = meta.dictionary
        js = json_encode(obj=dictionary)
        value = utf8_encode(string=js)
        key = self.__cache_name(identifier=identifier)
        return await self.set(name=key, value=value, expires=self.EXPIRES)
