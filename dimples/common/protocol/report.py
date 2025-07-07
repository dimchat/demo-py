# -*- coding: utf-8 -*-
#
#   DIMP : Decentralized Instant Messaging Protocol
#
#                                Written in 2020 by Moky <albert.moky@gmail.com>
#
# ==============================================================================
# MIT License
#
# Copyright (c) 2020 Albert Moky
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
    Report Protocol
    ~~~~~~~~~~~~~~~

    Report for online/offline, ...
"""

from typing import Any, Dict

from dimsdk import BaseCommand


class ReportCommand(BaseCommand):
    """
        Report Command
        ~~~~~~~~~~~~~~

        data format: {
            type : 0x88,
            sn   : 123,

            command : "report",
            title   : "online",   // or "offline"
            # ------ extra info
            time    : 1234567890
        }
    """

    REPORT = 'report'

    ONLINE = 'online'
    OFFLINE = 'offline'

    def __init__(self, content: Dict[str, Any] = None, title: str = None):
        if content is None:
            # 1. new command with title
            cmd = ReportCommand.REPORT
            super().__init__(cmd=cmd)
            if title is not None:
                self['title'] = title
        else:
            # 2. command info from network
            assert title is None, 'params error: %s, %s' % (content, title)
            super().__init__(content)

    #
    #   report title
    #
    @property
    def title(self) -> str:
        return self.get_str(key='title', default='')

    @title.setter
    def title(self, value: str):
        self['title'] = value
