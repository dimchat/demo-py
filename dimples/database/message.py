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

from typing import Optional, List, Dict

from dimsdk import SymmetricKey
from dimsdk import ID
from dimsdk import ReliableMessage

from ..utils import Config
from ..common import MessageDBI

from .t_group_keys import GroupKeysTable
from .t_cipherkey import CipherKeyTable
from .t_message import ReliableMessageTable


class MessageDatabase(MessageDBI):
    """
        Database for DaoKeDao
        ~~~~~~~~~~~~~~~~~~~~~
    """

    def __init__(self, config: Config):
        super().__init__()
        self._group_keys_table = GroupKeysTable(config=config)
        self._cipher_table = CipherKeyTable(config=config)
        self._msg_table = ReliableMessageTable(config=config)

    def show_info(self):
        self._group_keys_table.show_info()
        self._cipher_table.show_info()
        self._msg_table.show_info()

    #
    #   GroupKeys DBI

    # Override
    async def get_group_keys(self, group: ID, sender: ID) -> Optional[Dict[str, str]]:
        return await self._group_keys_table.get_group_keys(group=group, sender=sender)

    # Override
    async def save_group_keys(self, group: ID, sender: ID, keys: Dict[str, str]) -> bool:
        return await self._group_keys_table.save_group_keys(group=group, sender=sender, keys=keys)

    #
    #   CipherKey DBI
    #

    # Override
    async def get_cipher_key(self, sender: ID, receiver: ID, generate: bool = False) -> Optional[SymmetricKey]:
        return await self._cipher_table.get_cipher_key(sender=sender, receiver=receiver, generate=generate)

    # Override
    async def cache_cipher_key(self, key: SymmetricKey, sender: ID, receiver: ID):
        return await self._cipher_table.cache_cipher_key(key=key, sender=sender, receiver=receiver)

    #
    #   ReliableMessage DBI
    #

    # Override
    async def get_reliable_messages(self, receiver: ID, limit: int = 1024) -> List[ReliableMessage]:
        return await self._msg_table.get_reliable_messages(receiver=receiver, limit=limit)

    # Override
    async def cache_reliable_message(self, msg: ReliableMessage, receiver: ID) -> bool:
        return await self._msg_table.cache_reliable_message(msg=msg, receiver=receiver)

    # Override
    async def remove_reliable_message(self, msg: ReliableMessage, receiver: ID) -> bool:
        return await self._msg_table.remove_reliable_message(msg=msg, receiver=receiver)
