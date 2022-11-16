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
    Utils
    ~~~~~

    I'm too lazy to write codes for demo project, so I borrow some utils here
    from the <dimsdk> packages, but I don't suggest you to do it also, because
    I won't promise these private utils will not be changed. Hia hia~ :P
                                             -- Albert Moky @ Jan. 23, 2019
"""

from dimsdk import md5, sha1, sha256
from dimsdk import base64_encode, base64_decode
from dimsdk import utf8_encode, utf8_decode
from dimsdk import hex_encode, hex_decode
from dimsdk import json_encode, json_decode
from dimplugins.aes import random_bytes

from startrek.fsm import Runnable, Runner

from .singleton import Singleton
from .log import Log, Logging
from .dos import Path, File, TextFile, JSONFile
from .cache import CachePool, CacheHolder, CacheManager


__all__ = [

    'md5', 'sha1', 'sha256',
    'base64_encode', 'base64_decode',
    'utf8_encode', 'utf8_decode',
    'hex_encode', 'hex_decode',
    'json_encode', 'json_decode',
    'random_bytes',

    'Runnable', 'Runner',

    'Singleton',
    'Log', 'Logging',
    'Path', 'File', 'TextFile', 'JSONFile',
    'CachePool', 'CacheHolder', 'CacheManager',
]
