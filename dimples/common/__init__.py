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
    Common module
    ~~~~~~~~~~~~~

"""

from .protocol import *
from .dbi import *

from .anonymous import Anonymous
from .register import Register
from .ans import AddressNameServer, ANSFactory

from .checker import EntityChecker
from .archivist import CommonArchivist
from .facebook import CommonFacebook
from .messenger import CommonMessenger
from .packer import CommonMessagePacker
from .processer import CommonMessageProcessor
from .queue import SuspendedMessageQueue
from .session import Transmitter, Session


__all__ = [

    'MetaVersion',
    'Password',
    'BroadcastUtils',

    #
    #   protocol
    #

    'AnsCommand',

    'HandshakeCommand', 'HandshakeState',
    'LoginCommand',

    'BlockCommand',
    'MuteCommand',

    'ReportCommand',

    'GroupKeyCommand',

    'CustomizedContent', 'AppCustomizedContent',

    #
    #   Database Interface
    #

    'PrivateKeyDBI', 'MetaDBI', 'DocumentDBI',
    'UserDBI', 'ContactDBI', 'GroupDBI', 'GroupHistoryDBI',
    'AccountDBI',

    'ReliableMessageDBI', 'CipherKeyDBI', 'GroupKeysDBI',
    'MessageDBI',

    'ProviderDBI', 'StationDBI', 'LoginDBI',
    'SessionDBI',

    'ProviderInfo', 'StationInfo',

    #
    #   common
    #

    'Anonymous',
    'AddressNameServer', 'ANSFactory',

    'EntityChecker',
    'CommonArchivist',
    'CommonFacebook',

    'CommonMessenger',
    'CommonMessagePacker',
    'CommonMessageProcessor',
    'SuspendedMessageQueue',

    'Transmitter',
    'Session',

    'Register',

]
