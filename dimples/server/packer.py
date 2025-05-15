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

from ..common import CommonFacebook
from ..common import CommonMessagePacker


class ServerMessagePacker(CommonMessagePacker):

    @property
    def facebook(self) -> Optional[CommonFacebook]:
        barrack = super().facebook
        assert isinstance(barrack, CommonFacebook), 'barrack error: %s' % barrack
        return barrack

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
