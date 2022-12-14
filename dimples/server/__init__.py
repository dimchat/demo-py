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

from .push_info import PushAlert, PushInfo
from .push_service import PushService, PushCenter
from .pusher import Pusher, DefaultPusher

from .dispatcher import Roamer, Deliver, Worker
from .dispatcher import Dispatcher
from .deliver import UserDeliver, BotDeliver, StationDeliver
from .delivers import GroupDeliver, BroadcastDeliver
from .delivering import DeliverWorker, DefaultRoamer
from .filter import Filter, DefaultFilter

from .messenger import ServerMessenger
from .packer import ServerMessagePacker
from .processor import ServerMessageProcessor, ServerContentProcessorCreator


__all__ = [

    #
    #   CPU
    #
    'HandshakeCommandProcessor', 'LoginCommandProcessor', 'ReportCommandProcessor',
    'DocumentCommandProcessor', 'ReceiptCommandProcessor',

    # Session
    'ServerSession', 'SessionCenter',  # 'SessionPool',

    # Push Notification
    'PushAlert', 'PushInfo', 'PushService', 'PushCenter',
    'Pusher', 'DefaultPusher',

    # Deliver
    'Roamer', 'Deliver', 'Worker',
    'Dispatcher',
    'UserDeliver', 'BotDeliver', 'StationDeliver',
    'GroupDeliver', 'BroadcastDeliver',
    'DeliverWorker', 'DefaultRoamer',
    'Filter', 'DefaultFilter',

    'ServerMessenger',
    'ServerMessagePacker',
    'ServerMessageProcessor',
    'ServerContentProcessorCreator',
]
