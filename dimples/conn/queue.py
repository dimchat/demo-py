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

"""
    Message Queue
    ~~~~~~~~~~~~~

    for gate keeper
"""

import threading
from typing import Optional, List, Dict

from dimsdk import DateTime
from dimsdk import ReliableMessage

from startrek import Arrival, Departure
from startrek import ShipStatus


class MessageWrapper(Departure):

    def __init__(self, msg: ReliableMessage, ship: Departure):
        super().__init__()
        self.__msg = msg
        self.__ship = ship

    @property
    def msg(self) -> Optional[ReliableMessage]:
        return self.__msg

    @property
    def ship(self) -> Departure:
        return self.__ship

    @property  # Override
    def sn(self):
        return self.ship.sn

    @property  # Override
    def priority(self) -> int:
        return self.ship.priority

    @property  # Override
    def fragments(self) -> List[bytes]:
        return self.ship.fragments

    # Override
    def check_response(self, ship: Arrival) -> bool:
        return self.ship.check_response(ship=ship)

    @property  # Override
    def is_important(self) -> bool:
        return self.ship.is_important

    # Override
    def touch(self, now: float):
        return self.ship.touch(now=now)

    # Override
    def get_status(self, now: float) -> ShipStatus:
        return self.ship.get_status(now=now)


class MessageQueue:

    def __init__(self):
        super().__init__()
        self.__priorities: List[int] = []
        self.__fleets: Dict[int, List[MessageWrapper]] = {}  # priority => List[MessageWrapper]
        self.__lock = threading.Lock()
        # purge
        self.__next_purge_time = 0

    def append(self, msg: ReliableMessage, ship: Departure) -> bool:
        priority = ship.priority
        with self.__lock:
            # 1. choose an array with priority
            fleet = self.__fleets.get(priority)
            if fleet is None:
                # 1.1. create new array for this priority
                fleet = []
                self.__fleets[priority] = fleet
                # 1.2. insert the priority in a sorted list
                self.__insert(priority=priority)
            else:
                # 1.3. check duplicated
                signature = msg.get('signature')
                for wrapper in fleet:
                    item = wrapper.msg
                    if self.__is_duplicated(item, msg):
                        print('[QUEUE] duplicated message: %s' % signature)
                        return False
            # 2. append with wrapper
            wrapper = MessageWrapper(msg=msg, ship=ship)
            fleet.append(wrapper)
            return True

    # noinspection PyMethodMayBeStatic
    def __is_duplicated(self, msg1: ReliableMessage, msg2: ReliableMessage) -> bool:
        if msg1 is None or msg2 is None:
            return False
        sig1 = msg1.get('signature')
        sig2 = msg2.get('signature')
        if sig1 is None or sig2 is None:
            # assert False, 'signature should not empty here: %s, %s' % (msg1, msg2)
            return False
        elif sig1 != sig2:
            return False
        # maybe it's a group message split for every members,
        # so we still need to check receiver here.
        to1 = msg1.receiver
        to2 = msg2.receiver
        assert to1 is not None and to2 is not None, 'receiver should not empty here: %s, %s' % (msg1, msg2)
        return to1 == to2

    def __insert(self, priority: int):
        index = 0
        for value in self.__priorities:
            if value == priority:
                # duplicated
                return False
            elif value > priority:
                # got it
                break
            else:
                # current value is smaller than the new value,
                # keep going
                index += 1
        # insert new value before the bigger one
        self.__priorities.insert(index, priority)
        return True

    def next(self) -> Optional[MessageWrapper]:
        """ Get next new message """
        with self.__lock:
            for priority in self.__priorities:
                # get first message
                fleet = self.__fleets.get(priority)
                if fleet is not None and len(fleet) > 0:
                    return fleet.pop(0)

    def purge(self):
        now = DateTime.now()
        if now < self.__next_purge_time:
            return -1
        else:
            # next purge after half a minute
            self.__next_purge_time = now.timestamp + 30
        with self.__lock:
            priorities = list(self.__priorities)
            for prior in priorities:
                # 1. get messages with priority
                fleet = self.__fleets.get(prior)
                if fleet is None:
                    # this priority is empty
                    self.__priorities.remove(prior)
                elif len(fleet) == 0:
                    # this priority is empty
                    self.__fleets.pop(prior, None)
                    self.__priorities.remove(prior)
