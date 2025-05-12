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

from typing import Tuple, List

from dimsdk import ID
from dimsdk import ReliableMessage
from dimsdk import Command, GroupCommand

from ...utils import template_replace

from .base import Storage


class GroupHistoryStorage(Storage):
    """
        Group History Command Storage
        ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

        file path: '.dim/protected/{ADDRESS}/group_history.js'
    """

    history_path = '{PROTECTED}/{ADDRESS}/group_history.js'

    def show_info(self):
        path = self.protected_path(self.history_path)
        print('!!!  group history path: %s' % path)

    def __history_path(self, group: ID) -> str:
        path = self.protected_path(self.history_path)
        return template_replace(path, key='ADDRESS', value=str(group.address))

    async def load_group_histories(self, group: ID) -> List[Tuple[GroupCommand, ReliableMessage]]:
        path = self.__history_path(group=group)
        self.info(msg='Loading group history from: %s' % path)
        array = await self.read_json(path=path)
        if array is None:
            # history not found
            return []
        assert isinstance(array, List), 'group history error: %s, %s' % (array, path)
        histories = []
        for item in array:
            cmd = item.get('cmd')
            msg = item.get('msg')
            cmd = Command.parse(content=cmd)
            msg = ReliableMessage.parse(msg=msg)
            if cmd is None or msg is None:
                self.error(msg='group history error: %s' % item)
                continue
            his = (cmd, msg)
            histories.append(his)
        return histories

    async def save_group_histories(self, group: ID, histories: List[Tuple[GroupCommand, ReliableMessage]]) -> bool:
        array = []
        for his in histories:
            # assert len(his) == 2, 'group history error: %s' % his
            cmd = his[0]
            msg = his[1]
            item = {
                'cmd': cmd.dictionary,
                'msg': msg.dictionary,
            }
            array.append(item)
        path = self.__history_path(group=group)
        self.info(msg='Saving %d group history(ies) into: %s' % (len(histories), path))
        return await self.write_json(container=array, path=path)
