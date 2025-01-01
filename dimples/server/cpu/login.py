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
    Command Processor for 'login'
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    login protocol
"""

from typing import List, Dict

from dimsdk import ID
from dimsdk import ReliableMessage
from dimsdk import Content

from dimsdk.cpu import BaseCommandProcessor

from ...utils import Logging
from ...common import LoginCommand
from ...common import CommonFacebook, CommonMessenger


class LoginCommandProcessor(BaseCommandProcessor, Logging):

    @property
    def facebook(self) -> CommonFacebook:
        barrack = super().facebook
        assert isinstance(barrack, CommonFacebook), 'facebook error: %s' % barrack
        return barrack

    @property
    def messenger(self) -> CommonMessenger:
        transceiver = super().messenger
        assert isinstance(transceiver, CommonMessenger), 'messenger error: %s' % transceiver
        return transceiver

    # Override
    async def process_content(self, content: Content, r_msg: ReliableMessage) -> List[Content]:
        assert isinstance(content, LoginCommand), 'command error: %s' % content
        sender = content.identifier
        # 1. check roaming station
        station = content.station
        if not isinstance(station, Dict):
            self.error(msg='login command error: %s -> %s' % (sender, content))
            self.error(msg='login command error: %s -> %s' % (sender, r_msg))
            return []
        # 2. store login command
        session = self.messenger.session
        db = session.database
        if not await db.save_login_command_message(user=sender, content=content, msg=r_msg):
            self.error(msg='login command error/expired: %s' % content)
            return []
        current = await self.facebook.current_user
        roaming = ID.parse(identifier=station.get('ID'))
        # assert isinstance(roaming, ID), 'login command error: %s' % content
        if not isinstance(roaming, ID):
            self.warning(msg='station ID not found: %s' % station)
        elif roaming != current.identifier:
            # user roaming to other station
            self.info(msg='user roaming: %s -> %s' % (sender, roaming))
            # let dispatcher to handle cached messages for roaming user
            add_roaming(user=sender, station=roaming)
            return []
        if sender != session.identifier:
            # forwarded login command
            self.info(msg='user login: %s -> %s, forwarded by %s' % (sender, roaming, session.identifier))
            return []
        # 3. update session flag
        session.set_active(active=True, when=content.time)
        # only respond the user login to this station
        self.info(msg='user login: %s -> %s' % (sender, roaming))
        text = 'Login received.'
        return self._respond_receipt(text=text, content=content, envelope=r_msg.envelope, extra={
            'template': 'Login command received: ${ID}.',
            'replacements': {
                'ID': str(sender),
            }
        })


def add_roaming(user: ID, station: ID):
    """ add roaming user to dispatcher """
    from ..dispatcher import Dispatcher
    dispatcher = Dispatcher()
    dispatcher.add_roaming(user=user, station=station)
