# -*- coding: utf-8 -*-
#
#   DIM-SDK : Decentralized Instant Messaging Software Development Kit
#
#                                Written in 2024 by Moky <albert.moky@gmail.com>
#
# ==============================================================================
# MIT License
#
# Copyright (c) 2024 Albert Moky
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

from typing import Optional, List

from dimsdk import ID, ANYONE, FOUNDER


class BroadcastUtils:

    @classmethod  # private
    def group_seed(cls, group: ID) -> Optional[str]:
        name = group.name
        if name is not None:
            length = len(name)
            if length > 0 and (length != 8 or name.lower() != 'everyone'):
                return name

    @classmethod  # protected
    def broadcast_founder(cls, group: ID) -> Optional[ID]:
        name = cls.group_seed(group=group)
        if name is None:
            # Consensus: the founder of group 'everyone@everywhere'
            #            'Albert Moky'
            return FOUNDER
        else:
            # DISCUSS: who should be the founder of group 'xxx@everywhere'?
            #          'anyone@anywhere', or 'xxx.founder@anywhere'
            return ID.parse(identifier=name + '.founder@anywhere')

    @classmethod  # protected
    def broadcast_owner(cls, group: ID) -> Optional[ID]:
        name = cls.group_seed(group=group)
        if name is None:
            # Consensus: the owner of group 'everyone@everywhere'
            #            'anyone@anywhere'
            return ANYONE
        else:
            # DISCUSS: who should be the owner of group 'xxx@everywhere'?
            #          'anyone@anywhere', or 'xxx.owner@anywhere'
            return ID.parse(identifier=name + '.owner@anywhere')

    @classmethod  # protected
    def broadcast_members(cls, group: ID) -> List[ID]:
        name = cls.group_seed(group=group)
        if name is None:
            # Consensus: the member of group 'everyone@everywhere'
            #            'anyone@anywhere'
            return [ANYONE]
        else:
            # DISCUSS: who should be the member of group 'xxx@everywhere'?
            #          'anyone@anywhere', or 'xxx.member@anywhere'
            owner = ID.parse(identifier=name + '.owner@anywhere')
            member = ID.parse(identifier=name + '.member@anywhere')
            return [owner, member]
