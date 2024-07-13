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

from typing import Optional, List, Dict

from dimsdk import md5, sha1, sha256, keccak256, ripemd160
from dimsdk import base64_encode, base64_decode, base58_encode, base58_decode
from dimsdk import hex_encode, hex_decode
from dimsdk import utf8_encode, utf8_decode
from dimsdk import json_encode, json_decode

from dimsdk import FrequencyChecker, RecentTimeChecker

from dimsdk import Converter
from dimsdk import DateTime
from dimsdk import ReliableMessage
from dimsdk import DocumentHelper

from dimplugins.crypto.aes import random_bytes

from startrek.skywalker import Singleton
from startrek.skywalker import Runnable, Daemon
from startrek.fsm import Delegate as StateDelegate
from startrek.net.socket import get_remote_address, get_local_address

from aiou import Path, File, TextFile, JSONFile

from .runner import PatchRunner as Runner
from .log import Log, Logging
from .cache import CachePool, SharedCacheManager

from .config import Config


def is_before(old_time: Optional[DateTime], new_time: Optional[DateTime]) -> bool:
    """ check whether new time is before old time """
    return DocumentHelper.is_before(old_time, new_time)


def get_msg_sig(msg: ReliableMessage) -> str:
    """ last 6 bytes (signature in base64) """
    sig = msg.get('signature')
    # assert isinstance(sig, str), 'signature error: %s' % sig
    sig = sig.strip()
    return sig[-8:]  # last 6 bytes (signature in base64)


def get_msg_traces(msg: ReliableMessage) -> List:
    traces = msg.get('traces')
    if traces is None:
        return []
    assert isinstance(traces, List), 'traces error: %s' % traces
    stations = []
    for item in traces:
        if isinstance(item, Dict):
            sid = item.get('ID')
        elif isinstance(item, str):
            sid = item
        else:
            Log.error(msg='trace item error: %s' % item)
            continue
        stations.append(sid)
    return stations


def get_msg_info(msg: ReliableMessage) -> str:
    sig = get_msg_sig(msg=msg)
    traces = get_msg_traces(msg=msg)
    group = msg.group
    if group is None:
        return '%s => %s [%s] %s, traces: %s' % (msg.sender, msg.receiver, msg.time, sig, traces)
    else:
        return '%s => %s, %s [%s] %s, traces: %s' % (msg.sender, msg.receiver, group, msg.time, sig, traces)


def template_replace(template: str, key: str, value: str) -> str:
    """ replace '{key}' with value """
    tag = '{%s}' % key
    return template.replace(tag, value)


__all__ = [

    'md5', 'sha1', 'sha256', 'keccak256', 'ripemd160',
    'base64_encode', 'base64_decode', 'base58_encode', 'base58_decode',
    'hex_encode', 'hex_decode',
    'utf8_encode', 'utf8_decode',
    'json_encode', 'json_decode',

    'random_bytes',

    'Converter',

    'Runnable', 'Runner', 'Daemon',
    'StateDelegate',

    'get_remote_address', 'get_local_address',


    'Singleton',
    'Log', 'Logging',
    'Path', 'File', 'TextFile', 'JSONFile',
    'CachePool', 'SharedCacheManager',

    'FrequencyChecker', 'RecentTimeChecker',

    'Config',

    'is_before',
    'get_msg_sig', 'get_msg_info',
    'template_replace',

]
