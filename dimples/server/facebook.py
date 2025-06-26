# -*- coding: utf-8 -*-
# ==============================================================================
# MIT License
#
# Copyright (c) 2023 Albert Moky
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
    Facebook for station
    ~~~~~~~~~~~~~~~~~~~~

    Barrack for cache entities
"""

from typing import Optional, List

from dimsdk import ID

from ..common import BroadcastUtils
from ..common import CommonFacebook


class ServerFacebook(CommonFacebook):

    #
    #   Group DataSource
    #

    # Override
    async def get_founder(self, identifier: ID) -> Optional[ID]:
        assert identifier.is_group, 'group ID error: %s' % identifier
        # check broadcast group
        if identifier.is_broadcast:
            # founder of broadcast group
            return BroadcastUtils.broadcast_founder(group=identifier)
        self.error(msg='DO NOT CALL ME: %s' % identifier)
        return None

    # Override
    async def get_owner(self, identifier: ID) -> Optional[ID]:
        assert identifier.is_group, 'group ID error: %s' % identifier
        # check broadcast group
        if identifier.is_broadcast:
            # owner of broadcast group
            return BroadcastUtils.broadcast_owner(group=identifier)
        self.error(msg='DO NOT CALL ME: %s' % identifier)
        return None

    # Override
    async def get_members(self, identifier: ID) -> List[ID]:
        assert identifier.is_group, 'group ID error: %s' % identifier
        # check broadcast group
        if identifier.is_broadcast:
            # members of broadcast group
            return BroadcastUtils.broadcast_members(group=identifier)
        self.error(msg='DO NOT CALL ME: %s' % identifier)
        return []

    # Override
    async def get_assistants(self, identifier: ID) -> List[ID]:
        self.error(msg='DO NOT CALL ME: %s' % identifier)
        return []

    #
    #   Organizational Structure
    #

    # Override
    async def get_administrators(self, group: ID) -> List[ID]:
        self.error(msg='DO NOT CALL ME: %s' % group)
        return []

    # Override
    async def save_administrators(self, administrators: List[ID], group: ID) -> bool:
        self.error(msg='DO NOT CALL ME: %s' % group)
        return False

    # Override
    async def save_members(self, members: List[ID], group: ID) -> bool:
        self.error(msg='DO NOT CALL ME: %s' % group)
        return False
