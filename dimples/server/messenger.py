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
    Messenger for request handler in station
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    Transform and send message
"""

from typing import List

from dimsdk import ID
from dimsdk import Station
from dimsdk import ReliableMessage
from dimsdk import MessageUtils

from ..common import CommonMessenger

from .packer import ServerMessagePacker
from .dispatcher import Dispatcher


class ServerMessenger(CommonMessenger):

    # Override
    async def handshake_success(self):
        session = self.session
        identifier = session.identifier
        remote_address = session.remote_address
        self.warning(msg='user login: %s, socket: %s' % (identifier, remote_address))
        # process suspended messages
        await self._resume_reliable_messages()

    async def _resume_reliable_messages(self):
        packer = self.packer
        assert isinstance(packer, ServerMessagePacker), 'message packer error: %s' % packer
        messages = packer.resume_reliable_messages()
        for msg in messages:
            msg.pop('error', None)
            self.info(msg='processing suspended message: %s -> %s' % (msg.sender, msg.receiver))
            try:
                responses = await self.process_reliable_message(msg=msg)
                for res in responses:
                    await self.send_reliable_message(msg=res, priority=1)
            except Exception as error:
                self.error(msg='failed to process incoming message: %s' % error)

    # Override
    async def process_reliable_message(self, msg: ReliableMessage) -> List[ReliableMessage]:
        session = self.session
        current = await self.facebook.current_user
        sid = current.identifier
        receiver = msg.receiver
        # call super
        responses = await super().process_reliable_message(msg=msg)
        # check for first handshake
        if receiver == Station.ANY or msg.group == Station.EVERY:
            # if this message sent to 'station@anywhere', or with group ID 'stations@everywhere',
            # it means the client doesn't have the station's meta (e.g.: first handshaking)
            # or visa maybe expired, here attach them to the first response.
            meta = await current.meta
            visa = await current.visa
            for res in responses:
                if res.sender == sid:
                    # let the first responding message to carry the station's meta & visa
                    MessageUtils.set_meta(meta=meta, msg=res)
                    MessageUtils.set_visa(visa=visa, msg=res)
                    break
        elif session.identifier == sid:
            # station bridge
            responses = await pick_out(messages=responses, bridge=sid)
        return responses


async def pick_out(messages: List[ReliableMessage], bridge: ID) -> List[ReliableMessage]:
    responses = []
    dispatcher = Dispatcher()
    for msg in messages:
        receiver = msg.receiver
        if receiver == bridge:
            # respond to the bridge
            responses.append(msg)
        else:
            # this message is not respond to the bridge, the receiver may be
            # roaming to other station, so deliver it via dispatcher here.
            await dispatcher.deliver_message(msg=msg, receiver=receiver)
    return responses
