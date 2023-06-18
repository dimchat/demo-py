# -*- coding: utf-8 -*-
#
#   DIM-SDK : Decentralized Instant Messaging Software Development Kit
#
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
import time
from typing import Union, Any, Dict, List, Set

from mkm.types import Mapper, Dictionary
from dimsdk import ID, ReliableMessage

from ..utils import Singleton


class TraceNode(Dictionary):
    """ Trace node with ID and time """

    @property
    def identifier(self) -> ID:
        return ID.parse(identifier=self.get('ID'))

    @property
    def time(self) -> float:
        return self.get_float(key='time')

    def __eq__(self, other) -> bool:
        """ Return self == other. """
        if self is other:
            return True
        elif isinstance(other, TraceNode):
            return self.time == other.time and self.identifier == other.identifier
        else:
            return False

    def __ne__(self, other) -> bool:
        """ Return self != other. """
        if self is other:
            return False
        elif isinstance(other, TraceNode):
            return self.time != other.time or self.identifier != other.identifier
        else:
            return True

    def __ge__(self, other) -> bool:
        """ Return self >= other. """
        if self is other:
            return True
        elif isinstance(other, TraceNode):
            return self.time >= other.time

    def __gt__(self, other) -> bool:
        """ Return self > other. """
        if self is other:
            return False
        elif isinstance(other, TraceNode):
            return self.time > other.time

    def __le__(self, other) -> bool:
        """ Return self <= other. """
        if self is other:
            return True
        elif isinstance(other, TraceNode):
            return self.time <= other.time

    def __lt__(self, other) -> bool:
        """ Return self < other. """
        if self is other:
            return False
        elif isinstance(other, TraceNode):
            return self.time < other.time

    @classmethod
    def create(cls, identifier: ID, when: float = None):
        if when is None:
            when = time.time()
        node = {
            'ID': str(identifier),
            'time': when,
        }
        return cls(dictionary=node)

    @classmethod
    def parse(cls, node: Union[dict, str, None]):  # -> Optional[TraceNode]:
        if node is None:
            return None
        elif isinstance(node, TraceNode):
            return node
        elif isinstance(node, str):
            node = {
                'ID': node,
            }
        # assert isinstance(node, dict), 'trace node error: %s' % node
        return cls(dictionary=node)

    @classmethod
    def convert(cls, nodes: List[Union[dict, str]]):  # -> List[TraceNode]:
        array = []
        for item in nodes:
            trace = cls.parse(node=item)
            if trace is not None:
                array.append(trace)
        return array

    @classmethod
    def revert(cls, nodes: List) -> List[Dict[str, Any]]:
        array = []
        for item in nodes:
            if isinstance(item, Mapper):
                array.append(item.dictionary)
            elif isinstance(item, Dict):
                array.append(item)
            elif isinstance(item, ID):
                array.append({
                    'ID': str(item),
                })
            elif isinstance(item, str):
                array.append({
                    'ID': item,
                })
                # array.append(item)
        return array


class TraceList:
    """ Trace list with message time """

    def __init__(self, msg_time: float, traces: List[TraceNode]):
        super().__init__()
        self.__time = msg_time
        self.__traces = traces

    @property
    def time(self) -> float:
        return self.__time

    @property
    def nodes(self) -> List[TraceNode]:
        return self.__traces

    def insert(self, node: TraceNode):
        """ insert trace node with ID and time """
        pos = len(self.__traces) - 1
        while pos >= 0:
            item = self.__traces[pos]
            if item == node:
                # already exists
                return False
            elif item < node:
                # insert after this position
                break
            pos -= 1
        # insert
        self.__traces.insert(pos + 1, node)
        return True

    def search(self, node: ID) -> int:
        """ search for node ID """
        pos = 0
        for item in self.__traces:
            if item.identifier == node:
                # got it
                return pos
            else:
                pos += 1
        # not found
        return -1


class TracePool:
    """ Trace pool for messages """

    EXPIRES = 3600 * 5

    def __init__(self):
        super().__init__()
        self._next_time = 0
        self.__caches: Dict[str, TraceList] = {}  # str(msg.signature) => TraceList

    def purge(self, now: float):
        """ remove expired traces """
        if now < self._next_time:
            return False
        expired = now - self.EXPIRES
        keys = set(self.__caches.keys())
        for sig in keys:
            cached = self.__caches.get(sig)
            if cached is None or cached.time < expired:
                self.__caches.pop(sig, None)
        # purge it next hour
        self._next_time = now + 3600
        return True

    def get_traces(self, msg: ReliableMessage) -> TraceList:
        sig = msg['signature']
        cached = self.__caches.get(sig)
        if cached is None:
            # cache not found, create a new one with message time
            when = msg.time
            cached = TraceList(msg_time=when, traces=[])
            self.__caches[sig] = cached
        return cached

    def set_traces(self, msg: ReliableMessage) -> TraceList:
        """ set traces from msg """
        cached = self.get_traces(msg=msg)
        traces = msg.get('traces')
        if traces is not None:
            array = TraceNode.convert(nodes=traces)
            for item in array:
                cached.insert(node=item)
        return cached

    def add_trace(self, msg: ReliableMessage, node: TraceNode) -> TraceList:
        """ add trace node """
        cached = self.get_traces(msg=msg)
        cached.insert(node=node)
        return cached


class LockedPool(TracePool):

    def __init__(self):
        super().__init__()
        self.__lock = threading.Lock()

    # Override
    def purge(self, now: float):
        if now < self._next_time:
            # we can treat the msg.time as real time for initial checking
            return False
        # if message time out, check with real time
        now = time.time()
        with self.__lock:
            super().purge(now=now)

    # Override
    def get_traces(self, msg: ReliableMessage) -> TraceList:
        with self.__lock:
            return super().get_traces(msg=msg)


@Singleton
class TraceManager:

    def __init__(self):
        super().__init__()
        self.__pool = LockedPool()

    def is_traced(self, msg: ReliableMessage, node: ID) -> bool:
        """ merge traces from msg into cached pool,
            after that, check whether this node exists
        """
        pool = self.__pool
        pool.purge(now=msg.time)  # call when verifying new message
        cached = pool.set_traces(msg=msg)
        return cached.search(node=node) >= 0

    def get_traces(self, msg: ReliableMessage) -> TraceList:
        """ merge traces from msg into cached pool """
        pool = self.__pool
        return pool.set_traces(msg=msg)

    def set_nodes(self, msg: ReliableMessage, nodes: Set[ID]):
        """ merge traces from msg into cached pool,
            after that, check for these nodes, append them if not exists,
            and then update traces in msg
        """
        now = time.time()
        pool = self.__pool
        cached = pool.get_traces(msg=msg)
        for item in nodes:
            if cached.search(node=item) < 0:
                cached.insert(node=TraceNode.create(identifier=item, when=now))
        msg['traces'] = TraceNode.revert(nodes=cached.nodes)

    def add_node(self, msg: ReliableMessage, node: ID):
        """ append this node into cached list,
            and then update traces in msg
        """
        pool = self.__pool
        cached = pool.add_trace(msg=msg, node=TraceNode.create(identifier=node))
        msg['traces'] = TraceNode.revert(nodes=cached.nodes)
