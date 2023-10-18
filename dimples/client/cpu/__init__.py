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
    Content Processing Unites
    ~~~~~~~~~~~~~~~~~~~~~~~~~

    Processors for contents
"""

from .text import TextContentProcessor

from .handshake import HandshakeCommandProcessor
from .login import LoginCommandProcessor

from .group import HistoryCommandProcessor, GroupCommandProcessor
from .grp_invite import InviteCommandProcessor
from .grp_expel import ExpelCommandProcessor
from .grp_join import JoinCommandProcessor
from .grp_quit import QuitCommandProcessor
from .grp_reset import ResetCommandProcessor
from .grp_query import QueryCommandProcessor
from .grp_resign import ResignCommandProcessor

from .creator import ClientContentProcessorCreator

__all__ = [

    'TextContentProcessor',

    'HandshakeCommandProcessor',
    'LoginCommandProcessor',

    'HistoryCommandProcessor',
    'GroupCommandProcessor',
    'InviteCommandProcessor', 'ExpelCommandProcessor',
    'JoinCommandProcessor', 'QuitCommandProcessor',
    'ResetCommandProcessor', 'QueryCommandProcessor',
    'ResignCommandProcessor',

    'ClientContentProcessorCreator',

]
