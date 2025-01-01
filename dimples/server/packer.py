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
    Common extensions for MessagePacker
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
"""

from typing import Optional, List, Dict

from dimsdk import EntityType, ID, ANYONE
from dimsdk import SecureMessage, ReliableMessage
from dimsdk import Station
from dimsdk import InstantMessage

from ..utils import Singleton, Logging
from ..common import HandshakeCommand
from ..common import CommonFacebook, CommonMessenger
from ..common import CommonMessagePacker
from ..common import Vestibule

from .trace import TraceManager


class ServerMessagePacker(CommonMessagePacker):

    def __init__(self, facebook: CommonFacebook, messenger: CommonMessenger):
        super().__init__(facebook=facebook, messenger=messenger)
        self.__waiting_list = Vestibule()

    @property
    def facebook(self) -> Optional[CommonFacebook]:
        barrack = super().facebook
        assert isinstance(barrack, CommonFacebook), 'barrack error: %s' % barrack
        return barrack

    @property
    def messenger(self) -> Optional[CommonMessenger]:
        transceiver = super().messenger
        assert isinstance(transceiver, CommonMessenger), 'transceiver error: %s' % transceiver
        return transceiver

    # Override
    def suspend_reliable_message(self, msg: ReliableMessage, error: Dict):
        self.__waiting_list.suspend_reliable_message(msg=msg, error=error)

    # Override
    def suspend_instant_message(self, msg: InstantMessage, error: Dict):
        self.__waiting_list.suspend_instant_message(msg=msg, error=error)

    def resume_reliable_messages(self) -> List[ReliableMessage]:
        return self.__waiting_list.resume_reliable_messages()

    def resume_instant_messages(self) -> List[InstantMessage]:
        return self.__waiting_list.resume_instant_messages()

    # noinspection PyMethodMayBeStatic
    async def _is_blocked(self, msg: ReliableMessage) -> bool:
        block_filter = FilterManager().block_filter
        return await block_filter.is_blocked(msg=msg)

    async def _is_traced(self, msg: ReliableMessage) -> bool:
        """ check & append current node in msg['traces'] """
        facebook = self.facebook
        current = await facebook.current_user
        node = current.identifier
        tm = TraceManager()
        is_traced = tm.is_traced(msg=msg, node=node)
        tm.add_node(msg=msg, node=node)
        return is_traced

    # Override
    async def deserialize_message(self, data: bytes) -> Optional[ReliableMessage]:
        msg = await super().deserialize_message(data=data)
        if msg is None:
            # message error
            return None
        sender = msg.sender
        receiver = msg.receiver
        #
        #  0. check block list
        #
        if await self._is_blocked(msg=msg):
            self.warning(msg='user is blocked: %s -> %s (group: %s)' % (sender, receiver, msg.group))
            return None
        #
        #  1. check duplicated
        #
        if await self._is_traced(msg=msg):
            # cycled message
            if sender.type == EntityType.STATION or receiver.type == EntityType.STATION:
                # ignore cycled station message
                self.warning(msg='drop cycled station message: %s -> %s' % (sender, receiver))
                return None
            elif receiver.is_broadcast:
                # ignore cycled broadcast message
                self.warning(msg='drop cycled broadcast message: %s -> %s' % (sender, receiver))
                return None
            self.warning(msg='cycled message: %s -> %s' % (sender, receiver))
        #
        #  2. check session
        #
        facebook = self.facebook
        messenger = self.messenger
        session = messenger.session
        current = await facebook.current_user
        station = current.identifier
        if receiver == station:
            # message to this station
            # maybe a meta command, document command, etc ...
            pass
        elif receiver == Station.ANY or receiver == ANYONE:
            # if receiver == 'station@anywhere':
            #     it must be the first handshake without station ID;
            # if receiver == 'anyone@anywhere':
            #     it should be other plain message without encryption.
            pass
        elif session.identifier is None or not session.active:
            # not login?
            # 2.1. suspend this message for waiting handshake
            error = {
                'message': 'user not login',
            }
            self.suspend_reliable_message(msg=msg, error=error)
            # 2.2. ask client to handshake again (with session key)
            #      this message won't be delivered before handshake accepted
            command = HandshakeCommand.ask(session=session.session_key)
            command['force'] = True
            await messenger.send_content(content=command, sender=station, receiver=sender, priority=-1)
            return None
        return msg

    # Override
    async def verify_message(self, msg: ReliableMessage) -> Optional[SecureMessage]:
        # check session ready
        if self._is_trusted(sender=msg.sender):
            # no need to verify message from this sender
            self.debug(msg='trusted sender: %s' % msg.sender)
            return msg
        # verify after sender is OK
        return await super().verify_message(msg=msg)

    def _is_trusted(self, sender: ID) -> bool:
        messenger = self.messenger
        session = messenger.session
        user = session.identifier
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


"""
    Filter
    ~~~~~~

    Filters for delivering message
"""


class BlockFilter(Logging):

    async def is_blocked(self, msg: ReliableMessage) -> bool:
        sender = msg.sender
        receiver = msg.receiver
        group = msg.group
        self.debug(msg='checking block-list for: %s -> %s (group: %s)' % (sender, receiver, group))
        # TODO: check block-list
        return False


class MuteFilter(Logging):
    """ Filter for Push Notification service """

    async def is_muted(self, msg: ReliableMessage) -> bool:
        if msg.get_bool(key='muted', default=False):
            return True
        sender = msg.sender
        receiver = msg.receiver
        group = msg.group
        self.debug(msg='checking mute-list for: %s -> %s (group: %s)' % (sender, receiver, group))
        if sender.type == EntityType.STATION or receiver.type == EntityType.STATION:
            # mute all messages for stations
            return True
        elif sender.type == EntityType.BOT:
            # mute group message from bot
            return receiver.is_group or group is not None or 'GF' in msg
        elif receiver.type == EntityType.BOT:
            # mute all messages to bots
            return True
        # TODO: check mute-list


@Singleton
class FilterManager:

    def __init__(self):
        super().__init__()
        self.__block_filter = BlockFilter()
        self.__mute_filter = MuteFilter()

    @property
    def block_filter(self) -> BlockFilter:
        return self.__block_filter

    @block_filter.setter
    def block_filter(self, delegate: BlockFilter):
        self.__block_filter = delegate

    @property
    def mute_filter(self) -> MuteFilter:
        return self.__mute_filter

    @mute_filter.setter
    def mute_filter(self, delegate: MuteFilter):
        self.__mute_filter = delegate
