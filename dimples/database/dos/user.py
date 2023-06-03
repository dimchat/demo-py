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

from typing import List, Optional

from dimsdk import ID

from ...common import UserDBI, ContactDBI

from .base import Storage
from .base import template_replace


class UserStorage(Storage, UserDBI, ContactDBI):
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
        self.info(msg='Loading users from: %s' % path)
        users = self.read_json(path=path)
        if users is None:
            # local users not found
            return []
        return ID.convert(array=users)

    # Override
    def save_local_users(self, users: List[ID]) -> bool:
        """ save local users into file """
        path = self.__users_path()
        self.info(msg='Saving local users into: %s' % path)
        return self.write_json(container=ID.revert(array=users), path=path)

    # Override
    def add_user(self, user: ID) -> bool:
        array = self.local_users()
        if user in array:
            self.warning(msg='user exists: %s, %s' % (user, array))
            return True
        array.insert(0, user)
        return self.save_local_users(users=array)

    # Override
    def remove_user(self, user: ID) -> bool:
        array = self.local_users()
        if user not in array:
            self.warning(msg='user not exists: %s, %s' % (user, array))
            return True
        array.remove(user)
        return self.save_local_users(users=array)

    # Override
    def current_user(self) -> Optional[ID]:
        array = self.local_users()
        if len(array) > 0:
            return array[0]

    # Override
    def set_current_user(self, user: ID) -> bool:
        array = self.local_users()
        if user in array:
            index = array.index(user)
            if index == 0:
                self.warning(msg='current user not changed: %s, %s' % (user, array))
                return True
            array.pop(index)
        array.insert(0, user)
        return self.save_local_users(users=array)

    #
    #   Contact DBI
    #

    # Override
    def contacts(self, user: ID) -> List[ID]:
        """ load contacts from file """
        path = self.__contacts_path(identifier=user)
        self.info(msg='Loading contacts from: %s' % path)
        contacts = self.read_json(path=path)
        if contacts is None:
            # contacts not found
            return []
        return ID.convert(array=contacts)

    # Override
    def save_contacts(self, contacts: List[ID], user: ID) -> bool:
        """ save contacts into file """
        path = self.__contacts_path(identifier=user)
        self.info(msg='Saving contacts into: %s' % path)
        return self.write_json(container=ID.revert(array=contacts), path=path)

    # Override
    def add_contact(self, contact: ID, user: ID) -> bool:
        array = self.contacts(user=user)
        if contact in array:
            self.warning(msg='contact exists: %s, user: %s' % (contact, user))
            return True
        array.append(contact)
        return self.save_contacts(contacts=array, user=user)

    # Override
    def remove_contact(self, contact: ID, user: ID) -> bool:
        array = self.contacts(user=user)
        if contact not in array:
            self.warning(msg='contact not exists: %s, user: %s' % (contact, user))
            return True
        array.remove(contact)
        return self.save_contacts(contacts=array, user=user)
