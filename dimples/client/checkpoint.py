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

import threading
from typing import Dict

from dimsdk import DateTime
from dimsdk import ReliableMessage

from ..utils import Singleton


class SigPool:
    """ Signature pool for messages """

    EXPIRES = 3600 * 5

    def __init__(self):
        super().__init__()
        self._next_time = 0
        self.__caches: Dict[str, float] = {}  # signature:receiver => timestamp

    def purge(self, now: DateTime):
        """ remove expired traces """
        timestamp = now.timestamp
        if timestamp < self._next_time:
            return False
        else:
            # purge it next hour
            self._next_time = timestamp + 3600
        expired = timestamp - self.EXPIRES
        keys = set(self.__caches.keys())
        for tag in keys:
            msg_time = self.__caches.get(tag)
            if msg_time is None or msg_time < expired:
                self.__caches.pop(tag, None)
        return True

    def duplicated(self, msg: ReliableMessage) -> bool:
        """ check whether duplicated """
        sig = msg.get('signature')
        assert sig is not None, 'message error: %s' % msg
        if len(sig) > 16:
            sig = sig[-16:]
        add = msg.receiver.address
        tag = '%s:%s' % (sig, add)
        cached = self.__caches.get(tag)
        if cached is not None:
            return True
        # cache not found, create a new one with message time
        when = msg.time
        if when is None:
            self.__caches[tag] = DateTime.current_timestamp()
        else:
            self.__caches[tag] = when.timestamp
        return False


class LockedSigPool(SigPool):

    def __init__(self):
        super().__init__()
        self.__lock = threading.Lock()

    # Override
    def purge(self, now: DateTime):
        if now.timestamp < self._next_time:
            # we can treat the msg.time as real time for initial checking
            return False
        # if message time out, check with real time
        now = DateTime.now()
        with self.__lock:
            super().purge(now=now)

    # Override
    def duplicated(self, msg: ReliableMessage) -> bool:
        with self.__lock:
            return super().duplicated(msg=msg)


@Singleton
class Checkpoint:
    """ Check for duplicate messages """

    def __init__(self):
        super().__init__()
        self.__pool = LockedSigPool()

    def duplicated(self, msg: ReliableMessage) -> bool:
        pool = self.__pool
        repeated = pool.duplicated(msg=msg)
        when = msg.time
        if when is not None:
            pool.purge(now=when)
        return repeated
