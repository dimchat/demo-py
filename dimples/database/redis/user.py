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

from typing import List, Optional

from dimsdk import ID

from ...utils import utf8_encode, utf8_decode

from .base import RedisCache


class UserCache(RedisCache):

    # user info cached in Redis will be removed after 30 minutes, after that
    # it will be reloaded from local storage if it's still need.
    EXPIRES = 1800  # seconds

    @property  # Override
    def db_name(self) -> Optional[str]:
        return 'mkm'

    @property  # Override
    def tbl_name(self) -> str:
        return 'user'

    """
        User contacts
        ~~~~~~~~~~~~~

        redis key: 'mkm.user.{ID}.contacts'
    """
    def __contacts_cache_name(self, identifier: ID) -> str:
        return '%s.%s.%s.contacts' % (self.db_name, self.tbl_name, identifier)

    async def save_contacts(self, contacts: List[ID], identifier: ID) -> bool:
        assert contacts is not None, 'contacts cannot be empty'
        contacts = ID.revert(array=contacts)
        text = '\n'.join(contacts)
        text = utf8_encode(string=text)
        key = self.__contacts_cache_name(identifier=identifier)
        return await self.set(name=key, value=text, expires=self.EXPIRES)

    async def get_contacts(self, identifier: ID) -> List[ID]:
        key = self.__contacts_cache_name(identifier=identifier)
        value = await self.get(name=key)
        if value is None:
            return []
        text = utf8_decode(data=value)
        return ID.convert(array=text.splitlines())
