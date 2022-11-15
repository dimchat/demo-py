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

from typing import Optional

from dimsdk import ID
from dimsdk import ReliableMessage

from ..common import SessionDBI, LoginCommand, ReportCommand

from .t_login import LoginTable
from .t_report import ReportTable


class SessionDatabase(SessionDBI):
    """
        Database for Session
        ~~~~~~~~~~~~~~~~~~~~
    """

    def __init__(self, root: str = None, public: str = None, private: str = None):
        super().__init__()
        self.__login_table = LoginTable(root=root, public=public, private=private)
        self.__report_table = ReportTable(root=root, public=public, private=private)

    def show_info(self):
        self.__login_table.show_info()
        self.__report_table.show_info()

    #
    #   Login DBI
    #

    def login_command_message(self, identifier: ID) -> (Optional[LoginCommand], Optional[ReliableMessage]):
        return self.__login_table.login_command_message(identifier=identifier)

    def save_login_command_message(self, identifier: ID, cmd: LoginCommand, msg: ReliableMessage) -> bool:
        return self.__login_table.save_login_command_message(identifier=identifier, cmd=cmd, msg=msg)

    #
    #   Report DBI
    #

    # Override
    def report_command_message(self, identifier: ID) -> (Optional[ReportCommand], Optional[ReliableMessage]):
        return self.__report_table.report_command_message(identifier=identifier)

    # Override
    def save_report_command_message(self, identifier: ID, cmd: ReportCommand, msg: ReliableMessage) -> bool:
        return self.__report_table.save_report_command_message(identifier=identifier, cmd=cmd, msg=msg)
