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

from ...common import GroupDBI

from .base import Storage
from .base import template_replace


class GroupStorage(Storage, GroupDBI):
    """
        Group Storage
        ~~~~~~~~~~~~~

        file path: '.dim/private/{ADDRESS}/members.js'
        file path: '.dim/private/{ADDRESS}/assistants.js'
        file path: '.dim/private/{ADDRESS}/administrators.js'
    """
    members_path = '{PRIVATE}/{ADDRESS}/members.js'
    assistants_path = '{PRIVATE}/{ADDRESS}/assistants.js'
    administrators_path = '{PRIVATE}/{ADDRESS}/administrators.js'

    def show_info(self):
        path1 = template_replace(self.members_path, 'PRIVATE', self._private)
        path2 = template_replace(self.assistants_path, 'PRIVATE', self._private)
        path3 = template_replace(self.administrators_path, 'PRIVATE', self._private)
        print('!!!        members path: %s' % path1)
        print('!!!     assistants path: %s' % path2)
        print('!!! administrators path: %s' % path3)

    def __members_path(self, identifier: ID) -> str:
        path = self.members_path
        path = template_replace(path, 'PRIVATE', self._private)
        return template_replace(path, 'ADDRESS', str(identifier.address))

    def __assistants_path(self, identifier: ID) -> str:
        path = self.assistants_path
        path = template_replace(path, 'PRIVATE', self._private)
        return template_replace(path, 'ADDRESS', str(identifier.address))

    def __administrators_path(self, identifier: ID) -> str:
        path = self.administrators_path
        path = template_replace(path, 'PRIVATE', self._private)
        return template_replace(path, 'ADDRESS', str(identifier.address))

    #
    #   Group DBI
    #

    # Override
    def members(self, group: ID) -> List[ID]:
        """ load members from file """
        path = self.__members_path(identifier=group)
        self.info(msg='Loading members from: %s' % path)
        users = self.read_json(path=path)
        if users is None:
            # members not found
            return []
        return ID.convert(array=users)

    # Override
    def save_members(self, members: List[ID], group: ID) -> bool:
        """ save members into file """
        path = self.__members_path(identifier=group)
        self.info(msg='Saving members into: %s' % path)
        return self.write_json(container=ID.revert(array=members), path=path)

    # Override
    def assistants(self, group: ID) -> List[ID]:
        """ load assistants from file """
        path = self.__assistants_path(identifier=group)
        self.info(msg='Loading assistants from: %s' % path)
        bots = self.read_json(path=path)
        if bots is None:
            # assistants not found
            return []
        return ID.convert(array=bots)

    # Override
    def save_assistants(self, assistants: List[ID], group: ID) -> bool:
        """ save assistants into file """
        path = self.__assistants_path(identifier=group)
        self.info(msg='Saving assistants into: %s' % path)
        return self.write_json(container=ID.revert(array=assistants), path=path)

    # Override
    def administrators(self, group: ID) -> List[ID]:
        """ load administrators from file """
        path = self.__administrators_path(identifier=group)
        self.info(msg='Loading administrators from: %s' % path)
        users = self.read_json(path=path)
        if users is None:
            # administrators not found
            return []
        return ID.convert(array=users)

    # Override
    def save_administrators(self, administrators: List[ID], group: ID) -> bool:
        """ save administrators into file """
        path = self.__administrators_path(identifier=group)
        self.info(msg='Saving administrators into: %s' % path)
        return self.write_json(container=ID.revert(array=administrators), path=path)
