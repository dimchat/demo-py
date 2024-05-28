# -*- coding: utf-8 -*-
# ==============================================================================
# MIT License
#
# Copyright (c) 2023 Albert Moky
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

from typing import Optional, Dict

from dimsdk import ID

from ...utils import template_replace
from ...common import GroupKeysDBI

from .base import Storage


class GroupKeysStorage(Storage, GroupKeysDBI):
    """
        Group Keys Storage
        ~~~~~~~~~~~~~~~~~~

        file path: '.dim/private/{GROUP_ADDRESS}/{SENDER_ADDRESS}.keys.js'
    """

    keys_path = '{PRIVATE}/{GROUP_ADDRESS}/{SENDER_ADDRESS}.keys.js'

    def show_info(self):
        path = self.private_path(self.keys_path)
        print('!!!     group keys path: %s' % path)

    def __keys_path(self, group: ID, sender: ID) -> str:
        path = self.private_path(self.keys_path)
        path = template_replace(path, key='SENDER_ADDRESS', value=str(sender.address))
        return template_replace(path, key='GROUP_ADDRESS', value=str(group.address))

    #
    #   Group Keys DBI
    #

    # Override
    async def get_group_keys(self, group: ID, sender: ID) -> Optional[Dict[str, str]]:
        """ load group keys from file """
        path = self.__keys_path(group=group, sender=sender)
        self.info(msg='Loading group keys from: %s' % path)
        return await self.read_json(path=path)

    # Override
    async def save_group_keys(self, group: ID, sender: ID, keys: Dict[str, str]) -> bool:
        """ save group keys into file """
        path = self.__keys_path(group=group, sender=sender)
        self.info(msg='Saving group keys into: %s' % path)
        return await self.write_json(container=keys, path=path)
