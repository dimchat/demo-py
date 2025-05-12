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

from typing import Optional, Union

from ...utils import template_replace
from ...utils import Log
from ...utils import Path
from ...utils import TextFile, JSONFile
from ...utils import Config


class Storage:
    """
        DOS Storage
        ~~~~~~~~~~~
    """

    def __init__(self, config: Config):
        super().__init__()
        self.__config = config

    @property
    def root_dir(self) -> str:
        path = self.__config.database_root
        if path is None:
            path = '/var/.dim'
        return path

    @property
    def public_dir(self) -> str:
        path = self.__config.database_public
        if path is None:
            path = Path.join(self.root_dir, 'public')
        return path

    @property
    def protected_dir(self) -> str:
        path = self.__config.database_protected
        if path is None:
            path = Path.join(self.root_dir, 'protected')
        return path

    @property
    def private_dir(self) -> str:
        path = self.__config.database_private
        if path is None:
            path = Path.join(self.root_dir, 'private')
        return path

    def public_path(self, template: str):
        """ replace '{PUBLIC}' with public directory """
        tag = '{PUBLIC}'
        if template.startswith(tag):
            # replace with tag
            return template_replace(template=template, key='PUBLIC', value=self.public_dir)
        elif template.startswith('/') or template.find(':') > 0:
            # absolute path
            return template
        else:
            # relative path
            return Path.join(self.public_dir, template)

    def protected_path(self, template: str):
        """ replace '{PROTECTED}' with protected directory """
        tag = '{PROTECTED}'
        if template.startswith(tag):
            # replace with tag
            return template_replace(template=template, key='PROTECTED', value=self.protected_dir)
        elif template.startswith('/') or template.find(':') > 0:
            # absolute path
            return template
        else:
            # relative path
            return Path.join(self.protected_dir, template)

    def private_path(self, template: str):
        """ replace '{PRIVATE}' with private directory """
        tag = '{PRIVATE}'
        if template.startswith(tag):
            # replace with tag
            return template_replace(template=template, key='PRIVATE', value=self.private_dir)
        elif template.startswith('/') or template.find(':') > 0:
            # absolute path
            return template
        else:
            # relative path
            return Path.join(self.private_dir, template)

    @classmethod
    async def read_text(cls, path: str) -> Optional[str]:
        try:
            return await TextFile(path=path).read()
        except Exception as error:
            Log.error(msg='Storage >\t%s' % error)

    @classmethod
    async def read_json(cls, path: str) -> Union[dict, list, None]:
        try:
            return await JSONFile(path=path).read()
        except Exception as error:
            Log.error(msg='Storage >\t%s' % error)

    @classmethod
    async def write_text(cls, text: str, path: str) -> bool:
        try:
            return await TextFile(path=path).write(text=text)
        except Exception as error:
            Log.error(msg='Storage >\t%s' % error)

    @classmethod
    async def write_json(cls, container: Union[dict, list], path: str) -> bool:
        try:
            return await JSONFile(path=path).write(container=container)
        except Exception as error:
            Log.error(msg='Storage >\t%s' % error)

    @classmethod
    async def append_text(cls, text: str, path: str) -> bool:
        try:
            return await TextFile(path=path).append(text=text)
        except Exception as error:
            Log.error(msg='Storage >\t%s' % error)

    #
    #  Logging
    #
    def debug(self, msg: str):
        Log.debug(msg='[DB] %s >\t%s' % (self.__class__.__name__, msg))

    def info(self, msg: str):
        Log.info(msg='[DB] %s >\t%s' % (self.__class__.__name__, msg))

    def warning(self, msg: str):
        Log.warning(msg='[DB] %s >\t%s' % (self.__class__.__name__, msg))

    def error(self, msg: str):
        Log.error(msg='[DB] %s >\t%s' % (self.__class__.__name__, msg))
