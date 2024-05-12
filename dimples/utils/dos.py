# -*- coding: utf-8 -*-
# ==============================================================================
# MIT License
#
# Copyright (c) 2019 Albert Moky
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

"""
    Disk Operating System
    ~~~~~~~~~~~~~~~~~~~~~

    File access
"""

import os
import sys
from typing import Optional, Union, AnyStr, Dict, List
import json


class Path:
    """
        Paths for main script
        ~~~~~~~~~~~~~~~~~~~~~
        #! /usr/bin/env python3
        import os
        import sys
        path = os.path.abspath(__file__)
        path = os.path.dirname(path)
        path = os.path.dirname(path)
        sys.path.insert(0, path)
    """

    @classmethod
    def dir(cls, path: str) -> str:
        # '/home/User/Documents' -> '/home/User'
        # '/home/User/Documents/file.txt' -> '/home/User/Documents'
        return os.path.dirname(path)

    @classmethod
    def abs(cls, path: str) -> str:
        # 'file.txt' -> '/home/User/Documents/file.txt'
        return os.path.abspath(path)

    @classmethod
    def add(cls, path: str):
        """ add system path """
        sys.path.insert(0, path)

    """
        Path Utils
        ~~~~~~~~~~
    """

    @classmethod
    def join(cls, parent: str, *children: str) -> str:
        return os.path.join(parent, *children)

    @classmethod
    def is_dir(cls, path: str) -> bool:
        return os.path.isdir(path)

    @classmethod
    def is_file(cls, path: str) -> bool:
        return os.path.isfile(path)

    @classmethod
    def exists(cls, path: str) -> bool:
        return os.path.exists(path)

    @classmethod
    def remove(cls, path: str) -> bool:
        if os.path.exists(path):
            os.remove(path)
            return True

    @classmethod
    def make_dirs(cls, directory: str) -> bool:
        if not os.path.exists(directory):
            os.makedirs(directory, exist_ok=True)
            return True
        elif os.path.isdir(directory):
            # directory exists
            return True
        else:
            raise IOError('%s exists but is not a directory!' % directory)


class File:
    """ Base File """

    def __init__(self, path: str):
        super().__init__()
        self.__path: str = path
        self.__data: Optional[AnyStr] = None

    @property
    def path(self) -> str:
        return self.__path

    def read(self, mode: str = 'rb', encoding: str = None) -> Optional[AnyStr]:
        if self.__data is not None:
            # get data from cache
            return self.__data
        if not Path.exists(path=self.__path):
            # file not found
            return None
        if not Path.is_file(path=self.__path):
            # the path is not a file
            raise IOError('%s is not a file' % self.__path)
        with open(self.__path, mode=mode, encoding=encoding) as file:
            self.__data = file.read()
        return self.__data

    def write(self, data: AnyStr, mode: str = 'wb', encoding: str = None) -> bool:
        directory = Path.dir(path=self.__path)
        if not Path.make_dirs(directory=directory):
            return False
        with open(self.__path, mode=mode, encoding=encoding) as file:
            if len(data) == file.write(data):
                # OK, update cache
                self.__data = data
                return True

    def append(self, data: AnyStr, mode: str = 'ab', encoding: str = None) -> bool:
        if not Path.exists(path=self.__path):
            # new file
            if mode is not None:
                mode = mode.replace('a', 'w')
            return self.write(data, mode=mode)
        # append to exists file
        with open(self.__path, mode=mode, encoding=encoding) as file:
            if len(data) == file.write(data):
                # OK, erase cache for next update
                self.__data = None
                return True


class BinaryFile:

    def __init__(self, path: str):
        super().__init__()
        self.__file = File(path=path)

    @property
    def path(self) -> str:
        return self.__file.path

    def read(self) -> Optional[bytes]:
        return self.__file.read(mode='rb')

    def write(self, data: bytes) -> bool:
        return self.__file.write(data=data, mode='wb')

    def append(self, data: bytes) -> bool:
        return self.__file.append(data=data, mode='ab')


class TextFile:

    def __init__(self, path: str):
        super().__init__()
        self.__file = File(path=path)

    @property
    def path(self) -> str:
        return self.__file.path

    def read(self, encoding: str = 'utf-8') -> Optional[str]:
        return self.__file.read(mode='r', encoding=encoding)

    def write(self, text: str, encoding: str = 'utf-8') -> bool:
        return self.__file.write(data=text, mode='w', encoding=encoding)

    def append(self, text: str, encoding: str = 'utf-8') -> bool:
        return self.__file.append(data=text, mode='a', encoding=encoding)


class JSONFile:

    def __init__(self, path: str):
        super().__init__()
        self.__file = TextFile(path=path)
        self.__container: Union[Dict, List, None] = None

    @property
    def path(self) -> str:
        return self.__file.path

    def read(self) -> Union[Dict, List, None]:
        if self.__container is not None:
            # get content from cache
            return self.__container
        # read as text file
        text = self.__file.read()
        if text is not None:
            # convert text string to JSON object
            self.__container = json.loads(text)
        return self.__container

    def write(self, container: Union[Dict, List]) -> bool:
        # convert JSON object to text string
        text = json.dumps(container)
        if text is None:
            raise ValueError('cannot convert to JSON string: %s' % container)
        if self.__file.write(text=text):
            # OK, update cache
            self.__container = container
            return True
