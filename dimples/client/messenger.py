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
    Messenger for client
    ~~~~~~~~~~~~~~~~~~~~

    Transform and send message
"""

import time
from typing import List

from dimsdk import EntityType, EVERYONE

from ..common import LoginCommand
from ..common import MessageDBI
from ..common import CommonMessenger, CommonFacebook
from ..common import Session


class ClientMessenger(CommonMessenger):

    USER_AGENT = 'DIMP/0.12 (Server; Linux; en-US) DIMCoreKit/0.8 (Terminal) DIM-by-GSP/2.0'

    def __init__(self, session: Session, facebook: CommonFacebook, database: MessageDBI):
        super().__init__(session=session, facebook=facebook, database=database)
        self.__last_login = 0

    # Override
    def process_package(self, data: bytes) -> List[bytes]:
        responses = super().process_package(data=data)
        if responses is None or len(responses) == 0:
            # nothing response, check last login time
            now = int(time.time())
            if 0 < self.__last_login < now - 3600:
                self.broadcast_login_command()
        return responses

    def broadcast_login_command(self):
        session = self.session
        uid = session.identifier
        assert uid is not None, 'user not login'
        if uid.type == EntityType.STATION:
            # the current user is a station,
            # it would not login to another station.
            return False
        from .session import ClientSession
        assert isinstance(session, ClientSession), 'session error: %s' % session
        self.__last_login = time.time()
        # create login command with station info
        cmd = LoginCommand(identifier=uid)
        cmd.agent = self.USER_AGENT
        cmd.station = session.station
        self.send_content(sender=uid, receiver=EVERYONE, content=cmd)
