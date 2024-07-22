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

from typing import Optional, List, Dict

from dimsdk import EntityType, ID
from dimsdk import Content, ReceiptCommand
from dimsdk import ReliableMessage

from ..utils import Log, Logging
from ..common import CommonFacebook
from ..common import SessionDBI
from ..common import LoginCommand


class MessageDeliver(Logging):
    """ Delegate for delivering message """

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

    async def push_message(self, msg: ReliableMessage, receiver: ID) -> Optional[List[Content]]:
        """
        Push message for receiver

        :param msg:      network message
        :param receiver: actual receiver
        :return: responses
        """
        assert receiver.is_user, 'receiver ID error: %s' % receiver
        assert receiver.type != EntityType.STATION, 'should not push message for station: %s' % receiver
        # 1. try to push message directly
        if await session_push(msg=msg, receiver=receiver) > 0:
            text = 'Message delivered.'
            cmd = ReceiptCommand.create(text=text, envelope=msg.envelope)
            cmd['recipient'] = str(receiver)
            return [cmd]
        # 2. get roaming station
        roaming = await get_roaming_station(receiver=receiver, database=self.database)
        if roaming is None:
            # login command not found
            # return None to tell the push center to push notification for it.
            return None
        # 3. redirect message to roaming station
        return await self.redirect_message(msg=msg, neighbor=roaming)

    async def redirect_message(self, msg: ReliableMessage, neighbor: Optional[ID]) -> Optional[List[Content]]:
        """
        Redirect message to neighbor station

        :param msg:      network message
        :param neighbor: neighbor station
        :return: responses
        """
        """ Redirect message to neighbor station """
        assert neighbor is None or neighbor.type == EntityType.STATION, 'neighbor station ID error: %s' % neighbor
        self.info(msg='redirect message %s => %s to neighbor station: %s' % (msg.sender, msg.receiver, neighbor))
        # 0. check current station
        current = self.facebook.current_user.identifier
        assert current.type == EntityType.STATION, 'current station ID error: %s' % current
        if neighbor == current:
            self.debug(msg='same destination: %s, msg %s => %s' % (neighbor, msg.sender, msg.receiver))
            # the user is roaming to current station, but it's not online now
            # return None to tell the push center to push notification for it.
            return None
        # 1. try to push message to neighbor station directly
        if neighbor is not None and await session_push(msg=msg, receiver=neighbor) > 0:
            text = 'Message redirected.'
            cmd = ReceiptCommand.create(text=text, envelope=msg.envelope)
            cmd['neighbor'] = str(neighbor)
            return [cmd]
        # 2. push message to bridge
        return await bridge_message(msg=msg, neighbor=neighbor, bridge=current)


async def bridge_message(msg: ReliableMessage, neighbor: Optional[ID], bridge: ID) -> List[Content]:
    """
    Redirect message to neighbor station via the station bridge
    if neighbor is None, try to broadcast

    :param msg:      network message
    :param neighbor: roaming station
    :param bridge:   current station
    :return: responses
    """
    # NOTE: the messenger will serialize this message immediately, so
    #       we don't need to clone this dictionary to avoid 'neighbor'
    #       be changed to another value before pushing to the bridge.
    # clone = msg.copy_dictionary()
    # msg = ReliableMessage.parse(msg=clone)
    if neighbor is None:
        # broadcast to all neighbor stations
        # except that ones already in msg['recipients']
        await session_push(msg=msg, receiver=bridge)
        # no need to respond receipt for this broadcast message
        return []
    else:
        assert neighbor != bridge, 'cannot bridge cycled message: %s' % neighbor
        msg['neighbor'] = str(neighbor)
    # push to the bridge
    if await session_push(msg=msg, receiver=bridge) == 0:
        # station bridge not found
        Log.warning(msg='failed to push message to bridge: %s, drop message: %s -> %s'
                        % (bridge, msg.sender, msg.receiver))
        return []
    text = 'Message redirected via station bridge.'
    cmd = ReceiptCommand.create(text=text, envelope=msg.envelope)
    cmd['neighbor'] = str(neighbor)
    return [cmd]


async def session_push(msg: ReliableMessage, receiver: ID) -> int:
    """ push message via active session(s) of receiver """
    from .session_center import SessionCenter
    center = SessionCenter()
    active_sessions = center.active_sessions(identifier=receiver)
    success = 0
    for session in active_sessions:
        if await session.send_reliable_message(msg=msg):
            success += 1
    return success


async def get_roaming_station(receiver: ID, database: SessionDBI) -> Optional[ID]:
    """ get login command for roaming station """
    cmd, msg = await database.get_login_command_message(user=receiver)
    if isinstance(cmd, LoginCommand):
        station = cmd.station
        if isinstance(station, Dict):
            return ID.parse(identifier=station.get('ID'))
        else:
            Log.error(msg='login command error: %s -> %s' % (receiver, cmd))
            Log.error(msg='login command error: %s -> %s' % (receiver, msg))
