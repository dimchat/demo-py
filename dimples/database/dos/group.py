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

from ...common import GroupDBI

from .base import Storage
from .base import template_replace


class GroupStorage(Storage, GroupDBI):
    """
        Group Storage
        ~~~~~~~~~~~~~
        file path: '.dim/private/{ADDRESS}/members.js'
    """
    members_path = '{PRIVATE}/{ADDRESS}/members.js'

    def show_info(self):
        path = template_replace(self.members_path, 'PRIVATE', self._private)
        print('!!!   members path: %s' % path)

    def __members_path(self, identifier: ID) -> str:
        path = self.members_path
        path = template_replace(path, 'PRIVATE', self._private)
        return template_replace(path, 'ADDRESS', str(identifier.address))

    #
    #   Group DBI
    #

    # Override
    def founder(self, group: ID) -> Optional[ID]:
        # TODO: load group founder
        pass

    # Override
    def owner(self, group: ID) -> Optional[ID]:
        # TODO: load group owner
        pass

    # Override
    def members(self, group: ID) -> List[ID]:
        """ load members from file """
        path = self.__members_path(identifier=group)
        self.info(msg='Loading members from: %s' % path)
        contacts = self.read_json(path=path)
        if contacts is None:
            # members not found
            return []
        return ID.convert(array=contacts)

    # Override
    def save_members(self, members: List[ID], group: ID) -> bool:
        """ save members into file """
        path = self.__members_path(identifier=group)
        self.info(msg='Saving members into: %s' % path)
        return self.write_json(container=ID.revert(array=members), path=path)

    # Override
    def assistants(self, group: ID) -> List[ID]:
        # TODO: load group assistants
        self.warning(msg='TODO: load assistants: %s' % group)
        return []

    # Override
    def save_assistants(self, assistants: List[ID], group: ID) -> bool:
        # TODO: save assistants
        self.warning(msg='TODO: saving assistants: %s -> %s' % (group, assistants))
        return True
