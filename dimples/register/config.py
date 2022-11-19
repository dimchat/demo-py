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

from configparser import ConfigParser
from configparser import NoSectionError, NoOptionError
from typing import Optional

from ..utils import json_encode
from ..utils import Singleton
from ..common import AccountDBI
from ..database import AccountDatabase


class Config:

    def __init__(self, root: str, public: str, private: str):
        super().__init__()
        # database
        self.root = root
        self.public = public
        self.private = private

    def __str__(self) -> str:
        return self.to_json()

    def __repr__(self) -> str:
        return self.to_json()

    def to_json(self) -> str:
        info = {
            'database': {
                'root': self.root,
                'public': self.public,
                'private': self.private,
            },
        }
        return json_encode(obj=info)

    @classmethod
    def create(cls, root: str = None, public: str = None, private: str = None):
        # database
        if root is None:
            root = '/var/.dim'
        if public is None:
            public = '%s/public' % root    # /var/.dim/public
        if private is None:
            private = '%s/private' % root  # /var/.dim/private
        # create
        return cls(root=root, public=public, private=private)


class ConfigLoader:

    def __init__(self, file: str = None):
        super().__init__()
        parser = ConfigParser()
        parser.read(file)
        self.__parser = parser

    def _get_str(self, section: str, option: str) -> str:
        try:
            return self.__parser.get(section=section, option=option)
        except NoSectionError:
            pass
        except NoOptionError:
            pass

    def load(self) -> Config:
        # database
        root = self._get_str(section='database', option='root')
        public = self._get_str(section='database', option='public')
        private = self._get_str(section='database', option='private')
        # create config
        return Config.create(root=root, public=public, private=private)


@Singleton
class GlobalVariable:

    def __init__(self, config: Config):
        super().__init__()
        self.config = config
        self.adb: Optional[AccountDBI] = None


def init_database(shared: GlobalVariable):
    config = shared.config
    # create database
    adb = AccountDatabase(root=config.root, public=config.public, private=config.private)
    adb.show_info()
    shared.adb = adb
