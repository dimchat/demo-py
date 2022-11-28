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
    Message Dispatcher
    ~~~~~~~~~~~~~~~~~~

    A dispatcher to decide which way to deliver message.
"""

from abc import ABC, abstractmethod
from typing import Optional, List

from dimsdk import EntityType, ID
from dimsdk import Content
from dimsdk import ReliableMessage

from ..utils import Singleton


class Roamer(ABC):
    """ Delegate for redirect cached messages to roamed station """

    @abstractmethod
    def add_roaming(self, user: ID, station: ID) -> bool:
        """
        Add roaming user with station

        :param user:    roaming user
        :param station: station roamed to
        :return: False on error
        """
        raise NotImplemented


class Deliver(ABC):
    """ Delegate for deliver message """

    @abstractmethod
    def deliver_message(self, msg: ReliableMessage, receiver: ID) -> List[Content]:
        """
        Deliver message to destination

        :param msg:      message delivering
        :param receiver: message destination
        :return: responses
        """
        raise NotImplemented


class Worker(ABC):
    """ Actual deliver worker """

    @abstractmethod
    def push_message(self, msg: ReliableMessage, receiver: ID) -> List[Content]:
        """
        Push message to receiver

        :param msg:      network message
        :param receiver: actual receiver
        :return: None on failed
        """
        raise NotImplemented

    @abstractmethod
    def redirect_message(self, msg: ReliableMessage, neighbor: ID) -> List[Content]:
        """
        Redirect message to neighbor station

        :param msg:      network message
        :param neighbor: neighbor station
        :return: None on failed
        """
        raise NotImplemented


@Singleton
class Dispatcher(Deliver, Roamer):

    def __init__(self):
        super().__init__()
        # roaming user receptionist
        self.__roamer: Optional[Roamer] = None
        # deliver delegates
        self.__broadcast_deliver: Optional[Deliver] = None
        self.__group_deliver: Optional[Deliver] = None
        self.__station_deliver: Optional[Deliver] = None
        self.__bot_deliver: Optional[Deliver] = None
        self.__user_deliver: Optional[Deliver] = None
        # actually deliver worker
        self.__deliver_worker: Optional[Worker] = None

    def set_roamer(self, roamer: Roamer):
        self.__roamer = roamer

    def set_broadcast_deliver(self, deliver: Deliver):
        self.__broadcast_deliver = deliver

    def set_group_deliver(self, deliver: Deliver):
        self.__group_deliver = deliver

    @property
    def station_deliver(self) -> Deliver:
        """ deliver message for other stations """
        return self.__station_deliver

    def set_station_deliver(self, deliver: Deliver):
        self.__station_deliver = deliver

    @property
    def bot_deliver(self) -> Deliver:
        """ deliver message for bots """
        return self.__bot_deliver

    def set_bot_deliver(self, deliver: Deliver):
        self.__bot_deliver = deliver

    @property
    def user_deliver(self) -> Deliver:
        """ deliver message for users """
        return self.__user_deliver

    def set_user_deliver(self, deliver: Deliver):
        self.__user_deliver = deliver

    @property
    def deliver_worker(self) -> Worker:
        """ actual worker """
        return self.__deliver_worker

    def set_deliver_worker(self, worker: Worker):
        self.__deliver_worker = worker

    #
    #   Deliver
    #

    # Override
    def deliver_message(self, msg: ReliableMessage, receiver: ID) -> List[Content]:
        """ Deliver message to destination """
        # get actual deliver
        if receiver.is_broadcast:
            # broadcast message
            deliver = self.__broadcast_deliver
        elif receiver.is_group:
            # message to group assistants
            deliver = self.__group_deliver
        elif receiver.type == EntityType.STATION:
            # message to other stations
            deliver = self.__station_deliver
        elif receiver.type == EntityType.BOT:
            # message to a bot
            deliver = self.__bot_deliver
        else:
            # message to user
            deliver = self.__user_deliver
        # check deliver
        if deliver is None:
            self.error(msg='deliver not found for message %s: %s => %s' % (receiver, msg.sender, msg.receiver))
            return []
        return deliver.deliver_message(msg=msg, receiver=receiver)

    #
    #   Roamer
    #

    # Override
    def add_roaming(self, user: ID, station: ID) -> bool:
        """ Add roaming user with station """
        roamer = self.__roamer
        if roamer is not None:
            return roamer.add_roaming(user=user, station=station)
