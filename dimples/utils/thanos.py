# -*- coding: utf-8 -*-
#
#   DIM-SDK : Decentralized Instant Messaging Software Development Kit
#
#                                Written in 2019 by Moky <albert.moky@gmail.com>
#
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

from abc import ABC, abstractmethod
from typing import TypeVar, Generic
from typing import Optional


K = TypeVar('K')
V = TypeVar('V')


class MemoryCache(Generic[K, V], ABC):

    @abstractmethod
    def get(self, key: K) -> Optional[V]:
        raise NotImplemented

    @abstractmethod
    def put(self, key: K, value: Optional[V]):
        raise NotImplemented

    def reduce_memory(self) -> int:
        """ Garbage Collection """
        pass


class ThanosCache(MemoryCache[K, V]):

    def __init__(self):
        super().__init__()
        self.__caches = {}

    # Override
    def get(self, key: K) -> Optional[V]:
        return self.__caches.get(key)

    # Override
    def put(self, key: K, value: Optional[V]):
        self.__caches[key] = value

    # Override
    def reduce_memory(self) -> int:
        finger = 0
        finger = thanos(self.__caches, finger)
        return finger >> 1


def thanos(planet: dict, finger: int) -> int:
    """ Thanos can kill half lives of a world with a snap of the finger """
    people = planet.keys()
    for anybody in people:
        if (++finger & 1) == 1:
            # kill it
            planet.pop(anybody)
    return finger
