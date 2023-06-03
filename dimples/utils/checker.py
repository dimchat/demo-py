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

"""
    FrequencyChecker for Queries
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    Check for querying meta, document & group members
"""

import threading
import time
from typing import Generic, TypeVar, Dict

from dimsdk import ID

from ..utils import Singleton


K = TypeVar('K')


class FrequencyChecker(Generic[K]):
    """ Frequency checker for duplicated queries """

    def __init__(self, expires: float = 3600):
        super().__init__()
        self.__expires = expires
        self.__records: Dict[K, float] = {}

    def expired(self, key: K, now: float = None, force: bool = False) -> bool:
        if now is None:
            now = time.time()
        if force:
            # ignore last updated time, force to update now
            pass
        else:
            # check last update time
            expired = self.__records.get(key)
            if expired is not None and expired > now:
                # record exists and not expired yet
                return False
        self.__records[key] = now + self.__expires
        return True


@Singleton
class QueryFrequencyChecker:
    """ Synchronizer for Facebook """

    # each query will be expired after 10 minutes
    QUERY_EXPIRES = 600  # seconds

    def __init__(self):
        super().__init__()
        # query for meta
        self.__meta_queries: FrequencyChecker[ID] = FrequencyChecker(expires=self.QUERY_EXPIRES)
        self.__meta_lock = threading.Lock()
        # query for document
        self.__document_queries: FrequencyChecker[ID] = FrequencyChecker(expires=self.QUERY_EXPIRES)
        self.__document_lock = threading.Lock()
        # query for group members
        self.__members_queries: FrequencyChecker[ID] = FrequencyChecker(expires=self.QUERY_EXPIRES)
        self.__members_lock = threading.Lock()
        # response for document
        self.__document_responses: FrequencyChecker[ID] = FrequencyChecker(expires=self.QUERY_EXPIRES)

    def meta_query_expired(self, identifier: ID, now: float = None) -> bool:
        with self.__meta_lock:
            return self.__meta_queries.expired(key=identifier, now=now)

    def document_query_expired(self, identifier: ID, now: float = None) -> bool:
        with self.__document_lock:
            return self.__document_queries.expired(key=identifier, now=now)

    def members_query_expired(self, identifier: ID, now: float = None) -> bool:
        with self.__members_lock:
            return self.__members_queries.expired(key=identifier, now=now)

    def document_response_expired(self, identifier: ID, now: float = None, force: bool = False) -> bool:
        with self.__document_lock:
            return self.__document_responses.expired(key=identifier, now=now, force=force)
