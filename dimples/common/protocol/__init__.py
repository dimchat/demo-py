# -*- coding: utf-8 -*-
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

from dimsdk import Command
from dimsdk import CommandFactoryBuilder
from dimsdk import register_all_factories as register_core_factories
from dimplugins import register_plugins

from .handshake import HandshakeCommand, HandshakeState
from .login import LoginCommand
from .report import ReportCommand
from .ans import AnsCommand

from .mute import MuteCommand
from .block import BlockCommand

from .group import GroupKeyCommand


def register_all_factories():
    # Register core factories
    register_core_factories()

    # Handshake
    Command.register(cmd=HandshakeCommand.HANDSHAKE, factory=CommandFactoryBuilder(command_class=HandshakeCommand))
    # Login
    Command.register(cmd=LoginCommand.LOGIN, factory=CommandFactoryBuilder(command_class=LoginCommand))
    # Report
    Command.register(cmd=ReportCommand.REPORT, factory=CommandFactoryBuilder(command_class=ReportCommand))
    # ANS
    Command.register(cmd=AnsCommand.ANS, factory=CommandFactoryBuilder(command_class=AnsCommand))

    # Mute
    Command.register(cmd=MuteCommand.MUTE, factory=CommandFactoryBuilder(command_class=MuteCommand))
    # Block
    Command.register(cmd=BlockCommand.BLOCK, factory=CommandFactoryBuilder(command_class=BlockCommand))


__all__ = [

    'HandshakeCommand', 'HandshakeState',
    'LoginCommand',
    'ReportCommand',
    'AnsCommand',

    'BlockCommand',
    'MuteCommand',

    'GroupKeyCommand',

    'register_all_factories',
    'register_plugins',
]
