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

from ...common import UserDBI

from .base import Storage
from .base import template_replace


class UserStorage(Storage, UserDBI):
    """
        User Storage
        ~~~~~~~~~~~~
        file path: '.dim/private/users.js'
        file path: '.dim/private/{ADDRESS}/contacts.js'
    """
    users_path = '{PRIVATE}/users.js'
    contacts_path = '{PRIVATE}/{ADDRESS}/contacts.js'

    def show_info(self):
        path1 = template_replace(self.users_path, 'PRIVATE', self._private)
        path2 = template_replace(self.contacts_path, 'PRIVATE', self._private)
        print('!!!     users path: %s' % path1)
        print('!!!  contacts path: %s' % path2)

    def __users_path(self) -> str:
        path = self.users_path
        return template_replace(path, 'PRIVATE', self._private)

    def __contacts_path(self, identifier: ID) -> str:
        path = self.contacts_path
        path = template_replace(path, 'PRIVATE', self._private)
        return template_replace(path, 'ADDRESS', str(identifier.address))

    #
    #   User DBI
    #

    # Override
    def local_users(self) -> List[ID]:
        """ load users from file """
        path = self.__users_path()
        self.info('Loading users from: %s' % path)
        users = self.read_json(path=path)
        assert isinstance(users, list), 'local users not found: %s' % users
        return ID.convert(members=users)

    # Override
    def contacts(self, identifier: ID) -> List[ID]:
        """ load contacts from file """
        path = self.__contacts_path(identifier=identifier)
        self.info('Loading contacts from: %s' % path)
        contacts = self.read_json(path=path)
        if contacts is None:
            # contacts not found
            return []
        return ID.convert(members=contacts)

    # Override
    def save_local_users(self, users: List[ID]) -> bool:
        """ save local users into file """
        path = self.__users_path()
        self.info('Saving local users into: %s' % path)
        return self.write_json(container=ID.revert(members=users), path=path)

    # Override
    def save_contacts(self, contacts: List[ID], identifier: ID) -> bool:
        """ save contacts into file """
        path = self.__contacts_path(identifier=identifier)
        self.info('Saving contacts into: %s' % path)
        return self.write_json(container=ID.revert(members=contacts), path=path)
