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

from ...utils import template_replace
from ...common import GroupDBI

from .base import Storage


class GroupStorage(Storage, GroupDBI):
    """
        Group Storage
        ~~~~~~~~~~~~~

        file path: '.dim/protected/{ADDRESS}/members.js'
        file path: '.dim/protected/{ADDRESS}/assistants.js'
        file path: '.dim/protected/{ADDRESS}/administrators.js'
    """

    members_path = '{PROTECTED}/{ADDRESS}/members.js'
    assistants_path = '{PROTECTED}/{ADDRESS}/assistants.js'
    administrators_path = '{PROTECTED}/{ADDRESS}/administrators.js'

    def show_info(self):
        path1 = self.protected_path(self.members_path)
        path2 = self.protected_path(self.assistants_path)
        path3 = self.protected_path(self.administrators_path)
        print('!!!        members path: %s' % path1)
        print('!!!     assistants path: %s' % path2)
        print('!!! administrators path: %s' % path3)

    def __members_path(self, identifier: ID) -> str:
        path = self.protected_path(self.members_path)
        return template_replace(path, key='ADDRESS', value=str(identifier.address))

    def __assistants_path(self, identifier: ID) -> str:
        path = self.protected_path(self.assistants_path)
        return template_replace(path, key='ADDRESS', value=str(identifier.address))

    def __administrators_path(self, identifier: ID) -> str:
        path = self.protected_path(self.administrators_path)
        return template_replace(path, key='ADDRESS', value=str(identifier.address))

    #
    #   Group DBI
    #

    # Override
    async def get_founder(self, group: ID) -> Optional[ID]:
        pass

    # Override
    async def get_owner(self, group: ID) -> Optional[ID]:
        pass

    # Override
    async def get_members(self, group: ID) -> List[ID]:
        """ load members from file """
        path = self.__members_path(identifier=group)
        self.info(msg='Loading members from: %s' % path)
        users = await self.read_json(path=path)
        if users is None:
            # members not found
            return []
        return ID.convert(array=users)

    # Override
    async def save_members(self, members: List[ID], group: ID) -> bool:
        """ save members into file """
        path = self.__members_path(identifier=group)
        self.info(msg='Saving members into: %s' % path)
        return await self.write_json(container=ID.revert(array=members), path=path)

    # Override
    async def get_assistants(self, group: ID) -> List[ID]:
        """ load assistants from file """
        path = self.__assistants_path(identifier=group)
        self.info(msg='Loading assistants from: %s' % path)
        bots = await self.read_json(path=path)
        if bots is None:
            # assistants not found
            return []
        return ID.convert(array=bots)

    # Override
    async def save_assistants(self, assistants: List[ID], group: ID) -> bool:
        """ save assistants into file """
        path = self.__assistants_path(identifier=group)
        self.info(msg='Saving assistants into: %s' % path)
        return await self.write_json(container=ID.revert(array=assistants), path=path)

    # Override
    async def get_administrators(self, group: ID) -> List[ID]:
        """ load administrators from file """
        path = self.__administrators_path(identifier=group)
        self.info(msg='Loading administrators from: %s' % path)
        users = await self.read_json(path=path)
        if users is None:
            # administrators not found
            return []
        return ID.convert(array=users)

    # Override
    async def save_administrators(self, administrators: List[ID], group: ID) -> bool:
        """ save administrators into file """
        path = self.__administrators_path(identifier=group)
        self.info(msg='Saving administrators into: %s' % path)
        return await self.write_json(container=ID.revert(array=administrators), path=path)
