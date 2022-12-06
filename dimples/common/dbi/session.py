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

from abc import ABC, abstractmethod
from typing import Optional, Set, Tuple

from dimsdk import ID
from dimsdk import ReliableMessage

from ..protocol import LoginCommand
from ..protocol import ReportCommand


class LoginDBI(ABC):
    """ Login Command Table """

    #
    #   login command message
    #
    @abstractmethod
    def login_command_message(self, identifier: ID) -> (Optional[LoginCommand], Optional[ReliableMessage]):
        raise NotImplemented

    @abstractmethod
    def save_login_command_message(self, identifier: ID, content: LoginCommand, msg: ReliableMessage) -> bool:
        raise NotImplemented


class ReportDBI(ABC):
    """ Report(online/offline) Command Table """

    #
    #   online/offline command
    #
    @abstractmethod
    def online_command(self, identifier: ID) -> Optional[ReportCommand]:
        raise NotImplemented

    @abstractmethod
    def save_online_command(self, identifier: ID, content: ReportCommand) -> bool:
        raise NotImplemented


class ProviderDBI(ABC):
    """ Provider Stations Table """

    #
    #   neighbor stations
    #
    @abstractmethod
    def all_neighbors(self) -> Set[Tuple[str, int, Optional[ID]]]:
        """ get a set of (host, port, ID) """
        raise NotImplemented

    @abstractmethod
    def get_neighbor(self, host: str, port: int) -> Optional[ID]:
        raise NotImplemented

    @abstractmethod
    def add_neighbor(self, host: str, port: int, identifier: ID = None) -> bool:
        raise NotImplemented

    @abstractmethod
    def del_neighbor(self, host: str, port: int) -> Optional[ID]:
        raise NotImplemented


class SessionDBI(LoginDBI, ReportDBI, ProviderDBI, ABC):
    """ Session Database """
    pass
