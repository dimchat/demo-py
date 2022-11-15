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

from typing import Optional

from dimsdk import ID
from dimsdk import ReliableMessage
from dimsdk import Command

from ...common import LoginDBI, LoginCommand

from .base import Storage
from .base import template_replace


class LoginStorage(Storage, LoginDBI):
    """
        Login Command Storage
        ~~~~~~~~~~~~~~~~~~~~~
        file path: '.dim/private/{ADDRESS}/login.js'
    """

    login_path = '{PRIVATE}/{ADDRESS}/login.js'

    def show_info(self):
        path = template_replace(self.login_path, 'PRIVATE', self._private)
        print('!!! login cmd path: %s' % path)

    def __login_path(self, identifier: ID) -> str:
        path = self.login_path
        path = template_replace(path, 'PRIVATE', self._private)
        return template_replace(path, 'ADDRESS', str(identifier.address))

    #
    #   Login DBI
    #

    # Override
    def login_command_message(self, identifier: ID) -> (Optional[LoginCommand], Optional[ReliableMessage]):
        """ load login command from file """
        path = self.__login_path(identifier=identifier)
        self.info('Loading login command from: %s' % path)
        info = self.read_json(path=path)
        if info is None:
            # login command not found
            return None, None
        cmd = info.get('cmd')
        msg = info.get('msg')
        return Command.parse(content=cmd), ReliableMessage.parse(msg=msg)

    # Override
    def save_login_command_message(self, identifier: ID, cmd: LoginCommand, msg: ReliableMessage) -> bool:
        """ save login command into file """
        info = {
            'cmd': cmd.dictionary,
            'msg': msg.dictionary
        }
        path = self.__login_path(identifier=identifier)
        self.info('Saving login command into: %s' % path)
        return self.write_json(container=info, path=path)
