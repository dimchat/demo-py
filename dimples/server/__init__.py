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
    Server Module
    ~~~~~~~~~~~~~

"""

from .cpu import *

from .session import ServerSession
from .session_center import SessionCenter  # SessionPool

from .broadcast import BroadcastRecipientManager

from .push import BadgeKeeper, PushService
from .push import PushCenter

# from .dispatcher import Roamer, MessageDeliver, DeliverWorker
from .dispatcher import Dispatcher

from .trace import TraceNode, TraceList
from .trace import TraceManager

from .packer import BlockFilter, MuteFilter, FilterManager

from .packer import ServerMessagePacker
from .processor import ServerMessageProcessor, ServerContentProcessorCreator
from .messenger import ServerMessenger


__all__ = [

    #
    #   CPU
    #
    'HandshakeCommandProcessor', 'LoginCommandProcessor', 'ReportCommandProcessor',
    'AnsCommandProcessor', 'DocumentCommandProcessor', 'ReceiptCommandProcessor',

    # Session
    'ServerSession', 'SessionCenter',  # 'SessionPool',

    'BroadcastRecipientManager',

    # Push Notification
    'BadgeKeeper', 'PushService',
    'PushCenter',

    # Dispatcher
    # 'Roamer', 'MessageDeliver', 'DeliverWorker',
    'Dispatcher',

    # Trace
    'TraceNode', 'TraceList',
    'TraceManager',

    # Filter
    'BlockFilter', 'MuteFilter', 'FilterManager',

    'ServerMessagePacker',
    'ServerMessageProcessor', 'ServerContentProcessorCreator',
    'ServerMessenger',
]
