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

from typing import Optional

from dimsdk import EVERYONE
from dimsdk import Station
from dimsdk import DocumentCommand

from ..utils import Logging
from ..common import HandshakeCommand, ReportCommand
from ..common import CommonMessenger

from .session import ClientSession


class ClientMessenger(CommonMessenger, Logging):

    @property
    def session(self) -> ClientSession:
        sess = super().session
        assert isinstance(sess, ClientSession), 'session error: %s' % sess
        return sess

    def handshake(self, session_key: Optional[str]):
        """ send handshake command to current station """
        # 1. create handshake command
        if session_key is None:
            cmd = HandshakeCommand.start()
        else:
            cmd = HandshakeCommand.restart(session=session_key)
        # 2. send to remote station
        station = self.session.station
        self.send_content(sender=None, receiver=station.identifier, content=cmd, priority=-1)

    def handshake_success(self):
        """ callback for handshake success """
        # broadcast current documents after handshake success
        self.broadcast_document()

    def broadcast_document(self):
        """ broadcast meta & visa document to all stations """
        facebook = self.facebook
        current = facebook.current_user
        identifier = current.identifier
        meta = current.meta
        visa = current.visa
        cmd = DocumentCommand.response(identifier=identifier, meta=meta, document=visa)
        self.send_content(sender=None, receiver=EVERYONE, content=cmd, priority=-1)

    def report_online(self):
        """ send report command to keep user online """
        cmd = ReportCommand(title=ReportCommand.ONLINE)
        self.send_content(sender=None, receiver=Station.ANY, content=cmd, priority=1)

    def report_offline(self):
        """ set report command to let user offline """
        cmd = ReportCommand(title=ReportCommand.OFFLINE)
        self.send_content(sender=None, receiver=Station.ANY, content=cmd, priority=1)
