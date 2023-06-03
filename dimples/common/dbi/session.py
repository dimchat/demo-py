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
from typing import Optional, List, Tuple

from dimsdk import ID
from dimsdk import ReliableMessage

from ..protocol import LoginCommand


class LoginDBI(ABC):
    """ Login Command Table """

    #
    #   login command message
    #
    @abstractmethod
    def login_command_message(self, user: ID) -> Tuple[Optional[LoginCommand], Optional[ReliableMessage]]:
        raise NotImplemented

    @abstractmethod
    def save_login_command_message(self, user: ID, content: LoginCommand, msg: ReliableMessage) -> bool:
        raise NotImplemented


class ProviderDBI(ABC):
    """ Provider Stations Table """

    # default service provider
    GSP = 'gsp@everywhere'

    @abstractmethod
    def all_providers(self) -> List[Tuple[ID, int]]:
        """ get list of (SP_ID, chosen) """
        raise NotImplemented

    @abstractmethod
    def add_provider(self, provider: ID, chosen: int = 0) -> bool:
        raise NotImplemented

    @abstractmethod
    def update_provider(self, provider: ID, chosen: int) -> bool:
        raise NotImplemented

    @abstractmethod
    def remove_provider(self, provider: ID) -> bool:
        raise NotImplemented


SocketAddress = Tuple[str, int]


class StationDBI(ABC):

    @abstractmethod
    def all_stations(self, provider: ID) -> List[Tuple[SocketAddress, ID, int]]:
        """ get list of (host, port, SP_ID, chosen) """
        raise NotImplemented

    @abstractmethod
    def add_station(self, host: str, port: int, provider: ID, chosen: int = 0) -> bool:
        raise NotImplemented

    @abstractmethod
    def update_station(self, host: str, port: int, provider: ID, chosen: int) -> bool:
        raise NotImplemented

    @abstractmethod
    def remove_station(self, host: str, port: int, provider: ID) -> bool:
        raise NotImplemented

    @abstractmethod
    def remove_stations(self, provider: ID) -> bool:
        raise NotImplemented


# noinspection PyAbstractClass
class SessionDBI(LoginDBI, ProviderDBI, StationDBI, ABC):
    """ Session Database """
    pass
