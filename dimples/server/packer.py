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

from typing import Optional

from dimsdk import EntityType, ID
from dimsdk import SecureMessage, ReliableMessage

from ..utils import Singleton, Logging
from ..common import CommonFacebook
from ..common import CommonMessagePacker

from .trace import TraceManager


class ServerMessagePacker(CommonMessagePacker):

    def __current(self) -> ID:
        """ current station ID """
        facebook = get_facebook(packer=self)
        current = facebook.current_user
        sid = current.identifier
        assert sid is not None, 'current station error: %s' % current
        return sid

    def __is_traced(self, msg: ReliableMessage) -> bool:
        """ check & append current node in msg['traces'] """
        node = self.__current()
        tm = TraceManager()
        is_traced = tm.is_traced(msg=msg, node=node)
        tm.add_node(msg=msg, node=node)
        return is_traced

    def __is_trusted(self, sender: ID) -> bool:
        messenger = get_messenger(packer=self)
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

    # Override
    def deserialize_message(self, data: bytes) -> Optional[ReliableMessage]:
        msg = super().deserialize_message(data=data)
        if msg is not None:
            sender = msg.sender
            receiver = msg.receiver
            # check duplicated
            if self.__is_traced(msg=msg):
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
        return msg

    # Override
    def verify_message(self, msg: ReliableMessage) -> Optional[SecureMessage]:
        # check session ready
        if self.__is_trusted(sender=msg.sender):
            # no need to verify message from this sender
            self.debug(msg='trusted sender: %s' % msg.sender)
            return msg
        # verify after sender is OK
        return super().verify_message(msg=msg)


def get_facebook(packer: CommonMessagePacker) -> CommonFacebook:
    barrack = packer.facebook
    assert isinstance(barrack, CommonFacebook), 'facebook error: %s' % barrack
    return barrack


def get_messenger(packer: CommonMessagePacker):
    transceiver = packer.messenger
    from .messenger import ServerMessenger
    assert isinstance(transceiver, ServerMessenger), 'messenger error: %s' % transceiver
    return transceiver


"""
    Filter
    ~~~~~~

    Filters for delivering message
"""


class BlockFilter(Logging):

    def is_blocked(self, msg: ReliableMessage) -> bool:
        sender = msg.sender
        receiver = msg.receiver
        group = msg.group
        self.debug(msg='checking block-list for: %s -> %s (group: %s)' % (sender, receiver, group))
        # TODO: check block-list
        return False


class MuteFilter(Logging):
    """ Filter for Push Notification service """

    def is_muted(self, msg: ReliableMessage) -> bool:
        sender = msg.sender
        receiver = msg.receiver
        group = msg.group
        self.debug(msg='checking mute-list for: %s -> %s (group: %s)' % (sender, receiver, group))
        if sender.type == EntityType.STATION or receiver.type == EntityType.STATION:
            # mute all messages for stations
            return True
        elif sender.type == EntityType.BOT:
            # mute group message from bot
            return group is not None or receiver.is_group
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
