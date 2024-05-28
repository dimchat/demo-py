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

from typing import List

from dimsdk import ID

from ...utils import template_replace
from ...common import UserDBI, ContactDBI

from .base import Storage


class UserStorage(Storage, UserDBI, ContactDBI):
    """
        User Storage
        ~~~~~~~~~~~~
        file path: '.dim/private/{ADDRESS}/contacts.js'
    """

    contacts_path = '{PRIVATE}/{ADDRESS}/contacts.js'

    def show_info(self):
        path = self.private_path(self.contacts_path)
        print('!!!       contacts path: %s' % path)

    def __contacts_path(self, identifier: ID) -> str:
        path = self.private_path(self.contacts_path)
        return template_replace(path, key='ADDRESS', value=str(identifier.address))

    #
    #   User DBI
    #

    # Override
    async def get_local_users(self) -> List[ID]:
        return []

    # Override
    async def save_local_users(self, users: List[ID]) -> bool:
        pass

    #
    #   Contact DBI
    #

    # Override
    async def get_contacts(self, user: ID) -> List[ID]:
        """ load contacts from file """
        path = self.__contacts_path(identifier=user)
        self.info(msg='Loading contacts from: %s' % path)
        contacts = await self.read_json(path=path)
        if contacts is None:
            # contacts not found
            return []
        return ID.convert(array=contacts)

    # Override
    async def save_contacts(self, contacts: List[ID], user: ID) -> bool:
        """ save contacts into file """
        path = self.__contacts_path(identifier=user)
        self.info(msg='Saving contacts into: %s' % path)
        return await self.write_json(container=ID.revert(array=contacts), path=path)
