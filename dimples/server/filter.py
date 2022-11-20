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
    Filter
    ~~~~~~

    Filter for delivering message
"""

import weakref
from abc import ABC, abstractmethod

from dimsdk import EntityType, ID
from dimsdk import ReliableMessage

from ..common import CommonFacebook
from ..common import Session


class Filter(ABC):

    @abstractmethod
    def trusted_sender(self, sender: ID) -> bool:
        """
        Check whether ignore verifying message from this sender

        :param sender: remote user ID
        :return: True on trusted, ignore verifying
        """
        raise NotImplemented

    @abstractmethod
    def check_traced(self, msg: ReliableMessage) -> bool:
        """
        Check message traces for cycled message

        :param msg: network message
        :return: True on message already traced
        """
        raise NotImplemented


class DefaultFilter(Filter):

    def __init__(self, session: Session, facebook: CommonFacebook):
        super().__init__()
        self.__session = weakref.ref(session)
        self.__facebook = weakref.ref(facebook)

    @property
    def session(self) -> Session:
        return self.__session()

    @property
    def facebook(self) -> CommonFacebook:
        return self.__facebook()

    # Override
    def trusted_sender(self, sender: ID) -> bool:
        user = self.session.identifier
        if user is None:
            # current user not login yet
            return False
        # handshake accepted, check current user with sender
        if user == sender:
            # no need to verify signature of this message
            # which sender is equal to current id in session
            return True
        if user.type == EntityType.STATION:
            # if it's a roaming message delivered from another neighbor station,
            # shall we trust that neighbor totally and skip verifying too ???
            # TODO: trusted station list
            return True

    # Override
    def check_traced(self, msg: ReliableMessage) -> bool:
        # 1. get current node
        facebook = self.facebook
        current = facebook.current_user
        node = current.identifier
        assert node is not None, 'current station error: %s' % current
        # 2. check current node in msg['traces']
        is_traced = False
        traces = msg.get('traces')
        if traces is not None:
            for station in traces:
                # assert isinstance(station, str) or isinstance(station, dict)
                sid = station if isinstance(station, str) else station.get('ID')
                if node == sid:
                    is_traced = True
                    break
        # 3. append current node to msg['traces']
        if traces is None:
            # start from here
            msg['traces'] = [str(node)]
        else:
            # append current node
            traces.append(str(node))
        # OK
        return is_traced
