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

from .session import ServerSession
from .session_center import SessionCenter  # SessionPool

from .push import BadgeKeeper, PushService
from .push import PushCenter

from .deliver import MessageDeliver
from .dis_roamer import Roamer
from .dispatcher import Dispatcher

from .trace import TraceNode, TraceList
from .trace import TraceManager

from .packer import BlockFilter, MuteFilter, FilterManager

from .checker import ServerChecker
from .facebook import ServerFacebook
from .messenger import ServerMessenger
from .packer import ServerMessagePacker
from .processor import ServerMessageProcessor


__all__ = [

    # Session
    'ServerSession', 'SessionCenter',  # 'SessionPool',

    # Push Notification
    'BadgeKeeper', 'PushService',
    'PushCenter',

    # Dispatcher
    'MessageDeliver',
    'Roamer',
    'Dispatcher',

    # Trace
    'TraceNode', 'TraceList',
    'TraceManager',

    # Filter
    'BlockFilter', 'MuteFilter', 'FilterManager',

    #
    #   Server
    #

    'ServerChecker',

    'ServerFacebook',
    'ServerMessenger',
    'ServerMessagePacker',
    'ServerMessageProcessor',

]
