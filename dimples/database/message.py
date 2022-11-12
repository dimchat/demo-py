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

from typing import List

from dimsdk import ID
from dimsdk import ReliableMessage

from ..common import MessageDBI

from .t_message import ReliableMessageTable


class MessageDatabase(MessageDBI):
    """
        Database for DaoKeDao
        ~~~~~~~~~~~~~~~~~~~~~
    """

    def __init__(self, root: str = None, public: str = None, private: str = None):
        super().__init__()
        self.__msg_table = ReliableMessageTable(root=root, public=public, private=private)

    def show_info(self):
        self.__msg_table.show_info()

    #
    #   ReliableMessage DBI
    #

    # Override
    def reliable_messages(self, receiver: ID) -> List[ReliableMessage]:
        return self.__msg_table.reliable_messages(receiver=receiver)

    # Override
    def save_reliable_message(self, msg: ReliableMessage) -> bool:
        return self.__msg_table.save_reliable_message(msg=msg)

    # Override
    def remove_reliable_message(self, msg: ReliableMessage) -> bool:
        return self.__msg_table.remove_reliable_message(msg=msg)
