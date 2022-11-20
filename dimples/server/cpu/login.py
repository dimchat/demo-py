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

from typing import List

from dimsdk import ID
from dimsdk import ReliableMessage
from dimsdk import Content
from dimsdk import BaseCommandProcessor

from ...utils import Logging
from ...common import LoginCommand, ReportCommand
from ...common import CommonFacebook, CommonMessenger
from ...common import Session


class LoginCommandProcessor(BaseCommandProcessor, Logging):

    @property
    def facebook(self) -> CommonFacebook:
        barrack = super().facebook
        assert isinstance(barrack, CommonFacebook), 'facebook error: %s' % barrack
        return barrack

    @property
    def session(self) -> Session:
        messenger = self.messenger
        assert isinstance(messenger, CommonMessenger), 'messenger error: %s' % messenger
        return messenger.session

    # Override
    def process(self, content: Content, msg: ReliableMessage) -> List[Content]:
        assert isinstance(content, LoginCommand), 'command error: %s' % content
        sender = content.identifier
        # 1. store login command
        session = self.session
        db = session.database
        if not db.save_login_command_message(identifier=sender, cmd=content, msg=msg):
            self.error('login command error/expired: %s' % content)
            return []
        # 2. check roaming station
        current = self.facebook.current_user
        station = content.station
        roaming = ID.parse(identifier=station.get('ID'))
        assert isinstance(roaming, ID), 'login command error: %s' % content
        # TODO: post notification - USER_ONLINE
        # NotificationCenter().post(name=NotificationNames.USER_ONLINE, sender=self, info={
        #     'ID': str(sender),
        #     'station': str(roaming),
        #     'time': content.time,
        # })
        if roaming != current.identifier:
            # user roaming to other station
            self.info('user roaming: %s -> %s' % (sender, roaming))
            return []
        if sender != session.identifier:
            # forwarded login command
            self.info(msg='user login: %s -> %s, forwarded by %s' % (sender, roaming, session.identifier))
            return []
        # 3. update user online time
        cmd = ReportCommand(title=ReportCommand.ONLINE)
        if db.save_online_command(identifier=sender, cmd=cmd):
            session.active = True
        # only respond the user login to this station
        self.info('user login: %s -> %s' % (sender, roaming))
        return self._respond_text(text='Login received.')
