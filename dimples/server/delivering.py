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

from typing import Optional, List, Set

from dimsdk import EntityType, ID
from dimsdk import ReliableMessage

from ..common import LoginCommand
from ..common import CommonFacebook
from ..common import SessionDBI
from ..common import Session

from .session_center import SessionCenter
from .deliver import Roamer


class DefaultRoamer(Roamer):
    """ Deliver messages for roaming user """

    def __init__(self, database: SessionDBI, facebook: CommonFacebook):
        super().__init__()
        self.__database = database
        self.__facebook = facebook

    @property
    def database(self) -> Optional[SessionDBI]:
        return self.__database

    @property
    def facebook(self) -> Optional[CommonFacebook]:
        return self.__facebook

    # Override
    def roam_message(self, msg: ReliableMessage, receiver: ID) -> bool:
        """ Redirect message for other delivers """
        assert receiver.is_user, 'receiver error: %s' % receiver
        # get roaming station
        if receiver.type == EntityType.STATION:
            # station won't roaming to other station
            roaming = receiver
        else:
            # get roaming station from stored LoginCommand
            roaming = get_roaming_station(receiver=receiver, database=self.database)
            if roaming is None:
                # LoginCommand not found
                return False
        # get current station
        current = self.facebook.current_user.identifier
        assert current is not None, 'current station not set'
        if current == roaming:
            # same station, no need to redirect message
            return False
        # try to push to neighbor station directly,
        # if failed, try to push via the bridge
        return push_twice(msg=msg, target=receiver, roaming=roaming, bridge=current)

    # Override
    def roam_messages(self, messages: List[ReliableMessage], receiver: ID, roaming: ID) -> int:
        """ Redirect messages for dispatcher """
        current = self.facebook.current_user.identifier
        assert current is not None, 'current station not set'
        assert roaming != current, 'roaming station error: %s' % roaming
        center = SessionCenter()
        roaming_sessions = center.active_sessions(identifier=roaming)
        bridge_sessions = center.active_sessions(identifier=current)
        cnt = 0
        for msg in messages:
            if push_twice(msg=msg, target=receiver, roaming=roaming, bridge=current,
                          neighbor_sessions=roaming_sessions, bridge_sessions=bridge_sessions):
                cnt += 1
        return cnt


def get_roaming_station(receiver: ID, database: SessionDBI) -> Optional[ID]:
    """ get login command for roaming station """
    cmd, msg = database.login_command_message(identifier=receiver)
    if isinstance(cmd, LoginCommand):
        station = cmd.station
        assert isinstance(station, dict), 'login command error: %s' % cmd
        return ID.parse(identifier=station.get('ID'))


def push_once(msg: ReliableMessage, sessions: Set[Session]) -> bool:
    """ push message to neighbor station """
    for sess in sessions:
        if sess.send_reliable_message(msg=msg, priority=1):
            # delivered to first active session of other station,
            # actually there is only one session for one neighbor
            return True


def push_twice(msg: ReliableMessage, target: ID, roaming: ID, bridge: ID,
               neighbor_sessions: Set[Session] = None, bridge_sessions: Set[Session] = None) -> bool:
    """
    Deliver message to target station directly or via the station bridge

    :param msg:               network message
    :param target:            actual receiver
    :param roaming:           neighbor station ID
    :param bridge:            current station ID
    :param neighbor_sessions: for roaming station
    :param bridge_sessions:   for station bridge
    :return: True on pushed
    """
    center = SessionCenter()
    # 1. redirect cached messages to roaming station directly
    if neighbor_sessions is None:
        neighbor_sessions = center.active_sessions(identifier=roaming)
    if push_once(msg=msg, sessions=neighbor_sessions):
        # deliver to first active session of roaming station,
        # actually there is only one session for one neighbor
        return True
    # 2. roaming station not connected, redirect it via station bridge
    #    set roaming station ID here to let the bridge know where to go,
    #    and the bridge should remove 'target' before deliver it.
    msg['target'] = str(target)
    if bridge_sessions is None:
        bridge_sessions = center.active_sessions(identifier=bridge)
    if push_once(msg=msg, sessions=bridge_sessions):
        # deliver to first active session of station bridge,
        # actually there is only one session for the bridge
        return True
