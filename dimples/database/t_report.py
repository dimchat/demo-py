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

from ..utils import CacheManager
from ..common import ReportDBI
from ..common import ReportCommand


class ReportTable(ReportDBI):
    """ Implementations of ReportDBI """

    # noinspection PyUnusedLocal
    def __init__(self, root: str = None, public: str = None, private: str = None):
        super().__init__()
        man = CacheManager()
        self.__online_cache = man.get_pool(name='report.online')  # ID => ReportCommand

    # noinspection PyMethodMayBeStatic
    def show_info(self):
        print('!!!  online/offline in memory only !!!')

    #
    #   Report DBI
    #

    # Override
    def online_command(self, identifier: ID) -> Optional[ReportCommand]:
        value, _ = self.__online_cache.fetch(key=identifier)
        return value

    # Override
    def save_online_command(self, identifier: ID, cmd: ReportCommand) -> bool:
        # 1. check old record
        old = self.online_command(identifier=identifier)
        if old is not None and old.time >= cmd.time > 0:
            # command expired
            return False
        # 2. store into memory cache
        self.__online_cache.update(key=identifier, value=cmd, life_span=36000)
        return True
