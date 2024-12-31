# -*- coding: utf-8 -*-
#
#   DIM-SDK : Decentralized Instant Messaging Software Development Kit
#
#                                Written in 2022 by Moky <albert.moky@gmail.com>
#
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

"""
    FrequencyChecker for Queries
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    Check for querying meta, document & group members
"""

from typing import Generic, TypeVar, Optional, Dict

from startrek.types import Duration
from dimsdk import DateTime


K = TypeVar('K')


class FrequencyChecker(Generic[K]):
    """ Frequency checker for duplicated queries """

    def __init__(self, expires: Duration):
        super().__init__()
        self.__expires = expires
        self.__records: Dict[K, float] = {}  # ID -> seconds

    def __force_expired(self, key: K, now: DateTime):
        self.__records[key] = now + self.__expires
        return True

    def __check_expired(self, key: K, now: DateTime):
        expired = self.__records.get(key)
        if expired is not None and now < expired:
            # record exists and not expired yet
            return False
        self.__records[key] = now + self.__expires
        return True

    def is_expired(self, key: K, now: DateTime = None, force: bool = False) -> bool:
        if now is None:
            now = DateTime.now()
        # if force == true:
        #     ignore last updated time, force to update now
        # else:
        #     check last update time
        if force:
            return self.__force_expired(key=key, now=now)
        else:
            return self.__check_expired(key=key, now=now)


class RecentTimeChecker(Generic[K]):
    """ Recent time checker for querying """

    def __init__(self):
        super().__init__()
        self.__times: Dict[K, DateTime] = {}  # ID -> DateTime

    def set_last_time(self, key: K, now: Optional[DateTime]):
        if now is None:
            # assert False, 'recent time empty: %s' % key
            return False
        # TODO: calibration clock

        last = self.__times.get(key)
        if last is None or last < now:
            self.__times[key] = now
            return True
        # assert False, 'recent time empty: %s' % key

    def is_expired(self, key: K, now: Optional[DateTime]) -> bool:
        if now is None:
            # assert False, 'recent time empty: %s' % key
            return True
        last = self.__times.get(key)
        return last is not None and last > now
