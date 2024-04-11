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

from .archivist import CommonArchivist
from .facebook import CommonFacebook
from .messenger import CommonMessenger
from .packer import CommonMessagePacker
from .processer import CommonMessageProcessor
from .session import Transmitter, Session

from .compat import register_compatible_factories


register_all_factories()
register_plugins()
register_compatible_factories()


__all__ = [

    #
    #   protocol
    #
    'HandshakeCommand', 'HandshakeState',
    'LoginCommand',
    'ReportCommand',
    'AnsCommand',

    'BlockCommand',
    'MuteCommand',

    #
    #   Database Interface
    #
    'PrivateKeyDBI', 'MetaDBI', 'DocumentDBI',
    'UserDBI', 'ContactDBI', 'GroupDBI', 'GroupHistoryDBI',
    'AccountDBI',

    'ReliableMessageDBI', 'CipherKeyDBI', 'GroupKeysDBI',
    'MessageDBI',

    'LoginDBI', 'ProviderDBI', 'StationDBI',
    'SessionDBI',
    'ProviderInfo', 'StationInfo',

    #
    #   common
    #
    'Anonymous', 'Register',
    'AddressNameServer', 'ANSFactory',

    'CommonArchivist',
    'CommonFacebook',
    'CommonMessenger',
    'CommonMessagePacker',
    'CommonMessageProcessor',
    'Transmitter',
    'Session',

]
