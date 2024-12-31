# -*- coding: utf-8 -*-
# ==============================================================================
# MIT License
#
# Copyright (c) 2021 Albert Moky
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
    Database module
    ~~~~~~~~~~~~~~~

"""

import time
from typing import Optional, Set

from aiou.mem import CachePool, CacheManager
from aiou.mem.cache import K, V

from startrek.skywalker import Singleton
from startrek.skywalker import Runner

from .log import Logging


@Singleton
class SharedCacheManager(Runner, Logging):

    def __init__(self):
        super().__init__(interval=2.0)
        self.__manager = CacheManager()
        self.__next_time = 0
        self.start()

    def start(self):
        Runner.async_task(coro=self.run())

    # Override
    async def process(self) -> bool:
        # try to purge each 5 minutes
        now = time.time()
        if now < self.__next_time:
            return False
        else:
            self.__next_time = now + 300
        # purge
        try:
            count = self.purge(now=now)
            self.info(msg='[MEM] purge %d item(s) from cache pools' % count)
        except Exception as error:
            self.error(msg='[MEM] failed to purge cache: %s' % error)

    def all_names(self) -> Set[K]:
        """ get names of all pools """
        return self.__manager.all_names()

    def get_pool(self, name: str) -> CachePool[K, V]:
        """ get pool with name """
        return self.__manager.get_pool(name=name)

    def remove_pool(self, name: str) -> Optional[CachePool[K, V]]:
        """ remove pool with name """
        return self.__manager.remove_pool(name=name)

    def purge(self, now: float) -> int:
        """ purge all pools """
        return self.__manager.purge(now=now)
