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

from typing import Optional, Tuple

from dimsdk import ID
from dimsdk import ReliableMessage
from dimsdk import ResetCommand, ResetGroupCommand

from ...common import ResetGroupDBI

from .base import Storage
from .base import template_replace


class ResetGroupStorage(Storage, ResetGroupDBI):
    """
        Reset Group Command Storage
        ~~~~~~~~~~~~~~~~~~~~~~~~~~~

        file path: '.dim/private/{ADDRESS}/group_reset.js'
    """

    reset_path = '{PRIVATE}/{ADDRESS}/group_reset.js'

    def show_info(self):
        path = template_replace(self.reset_path, 'PRIVATE', self._private)
        print('!!!  reset grp cmd path: %s' % path)

    def __reset_path(self, identifier: ID) -> str:
        path = self.reset_path
        path = template_replace(path, 'PRIVATE', self._private)
        return template_replace(path, 'ADDRESS', str(identifier.address))

    #
    #   Login DBI
    #

    # Override
    def reset_command_message(self, group: ID) -> Tuple[Optional[ResetCommand], Optional[ReliableMessage]]:
        """ load reset group command from file """
        path = self.__reset_path(identifier=group)
        self.info(msg='Loading reset group command from: %s' % path)
        info = self.read_json(path=path)
        if info is None:
            # command not found
            return None, None
        cmd = info.get('cmd')
        msg = info.get('msg')
        if cmd is not None:
            cmd = ResetGroupCommand(content=cmd)
        return cmd, ReliableMessage.parse(msg=msg)

    # Override
    def save_reset_command_message(self, group: ID, content: ResetCommand, msg: ReliableMessage) -> bool:
        """ save reset group command into file """
        info = {
            'cmd': content.dictionary,
            'msg': msg.dictionary
        }
        path = self.__reset_path(identifier=group)
        self.info(msg='Saving reset group command into: %s' % path)
        return self.write_json(container=info, path=path)
