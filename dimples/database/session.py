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

from typing import Optional, List, Tuple

from dimsdk import ID
from dimsdk import ReliableMessage

from ..common import ProviderInfo, StationInfo
from ..common import SessionDBI, LoginCommand

from .t_login import LoginTable
from .t_station import StationTable


class SessionDatabase(SessionDBI):
    """
        Database for Session
        ~~~~~~~~~~~~~~~~~~~~
    """

    def __init__(self, root: str = None, public: str = None, private: str = None):
        super().__init__()
        self.__login_table = LoginTable(root=root, public=public, private=private)
        self.__station_table = StationTable(root=root, public=public, private=private)

    def show_info(self):
        self.__login_table.show_info()
        self.__station_table.show_info()

    #
    #   Login DBI
    #

    async def get_login_command_message(self, user: ID) -> Tuple[Optional[LoginCommand], Optional[ReliableMessage]]:
        return await self.__login_table.get_login_command_message(user=user)

    async def save_login_command_message(self, user: ID, content: LoginCommand, msg: ReliableMessage) -> bool:
        return await self.__login_table.save_login_command_message(user=user, content=content, msg=msg)

    #
    #   Provider DBI
    #

    # Override
    async def all_providers(self) -> List[ProviderInfo]:
        return await self.__station_table.all_providers()

    # Override
    async def add_provider(self, identifier: ID, chosen: int = 0) -> bool:
        return await self.__station_table.add_provider(identifier=identifier, chosen=chosen)

    # Override
    async def update_provider(self, identifier: ID, chosen: int) -> bool:
        return await self.__station_table.update_provider(identifier=identifier, chosen=chosen)

    # Override
    async def remove_provider(self, identifier: ID) -> bool:
        return await self.__station_table.remove_provider(identifier=identifier)

    #
    #   Station DBI
    #

    # Override
    async def all_stations(self, provider: ID) -> List[StationInfo]:
        return await self.__station_table.all_stations(provider=provider)

    # Override
    async def add_station(self, identifier: Optional[ID], host: str, port: int, provider: ID,
                          chosen: int = 0) -> bool:
        return await self.__station_table.add_station(identifier=identifier,
                                                      host=host, port=port, provider=provider, chosen=chosen)

    # Override
    async def update_station(self, identifier: Optional[ID], host: str, port: int, provider: ID,
                             chosen: int = 0) -> bool:
        return await self.__station_table.update_station(identifier=identifier,
                                                         host=host, port=port, provider=provider, chosen=chosen)

    # Override
    async def remove_station(self, host: str, port: int, provider: ID) -> bool:
        return await self.__station_table.remove_station(host=host, port=port, provider=provider)

    # Override
    async def remove_stations(self, provider: ID) -> bool:
        return await self.__station_table.remove_stations(provider=provider)
