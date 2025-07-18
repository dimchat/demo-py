# -*- coding: utf-8 -*-
#
#   DIMP : Decentralized Instant Messaging Protocol
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

from typing import List, Dict

from dimsdk import DateTime
from dimsdk import ID

from .customized import CustomizedContent


class GroupHistory:
    """ Group Query Command
        ~~~~~~~~~~~~~~~~~~~

        data format: {
            "type" : i2s(0xCC),
            "sn"   : 123,
            "time" : 123.456,

            "app"  : "chat.dim.group",
            "mod"  : "history",
            "act"  : "query",

            "group"     : "{GROUP_ID}",
            "last_time" : 0,             // Last group history time for querying
        }
    """

    APP = 'chat.dim.group'
    MOD = 'keys'

    ACT_QUERY = 'query'

    #
    #   Factory method
    #

    @classmethod
    def query_group_history(cls, group: ID, last_time: DateTime = None) -> CustomizedContent:
        """ QueryCommand is deprecated, use this method instead. """
        assert group.is_group, 'group ID error: %s' % group
        content = CustomizedContent.create(app=cls.APP, mod=cls.MOD, act=cls.ACT_QUERY)
        content.group = group
        if last_time is not None:
            # Last group history time for querying
            content.set_datetime(key='last_time', value=last_time)
        return content


class GroupKeys:
    """ Group Key Command
        ~~~~~~~~~~~~~~~~~

        data format: {
            "type" : i2s(0xCC),
            "sn"   : 123,
            "time" : 123.456,

            "app"  : "chat.dim.group",
            "mod"  : "keys",
            "act"  : "query",   // "update", "request", "respond"

            "group"  : "{GROUP_ID}",
            "from"   : "{SENDER_ID}",
            "to"     : ["{MEMBER_ID}", ],  // query for members
            "digest" : "{KEY_DIGEST}",     // query with digest
            "keys"   : {
                "digest"      : "{KEY_DIGEST}",
                "{MEMBER_ID}" : "{ENCRYPTED_KEY}",
            }
        }
    """

    APP = 'chat.dim.group'
    MOD = 'keys'

    # Group Key Actions:
    #
    #   1. when group bot found new member, or key digest updated,
    #      send a 'query' command to the message sender for new keys;
    #
    #   2. send all keys with digest to the group bot;
    #
    #   3. if a member received a group message with new key digest,
    #      send a 'request' command to the group bot;
    #
    #   4. send new key to the group member.
    #
    ACT_QUERY = 'query'      # 1. bot -> sender
    ACT_UPDATE = 'update'    # 2. sender -> bot
    ACT_REQUEST = 'request'  # 3. member -> bot
    ACT_RESPOND = 'respond'  # 4. bot -> member

    #
    #   Factory methods
    #

    @classmethod
    def create(cls, action: str, group: ID, sender: ID,
               members: List[ID] = None, digest: str = None,
               encoded_keys: Dict[str, str] = None) -> CustomizedContent:
        assert group.is_group, 'group ID error: %s' % group
        assert sender.is_user, 'user ID error: %s' % sender
        # 1. create group command
        content = CustomizedContent.create(app=cls.APP, mod=cls.MOD, act=action)
        content.group = group
        # 2. direction: sender -> members
        content['from'] = str(sender)
        if members is not None:
            content['to'] = ID.revert(identifiers=members)
        # 3. keys and digest
        if encoded_keys is not None:
            content['keys'] = encoded_keys
        elif digest is not None:
            content['digest'] = digest
        # OK
        return content

    # 1. bot -> sender: 'query'
    @classmethod
    def query_group_keys(cls, group: ID, sender: ID, members: List[ID], digest: str = None) -> CustomizedContent:
        """ Query group keys from sender """
        return cls.create(action=cls.ACT_QUERY, group=group, sender=sender, members=members, digest=digest)

    # 2. sender -> bot: 'update'
    @classmethod
    def update_group_keys(cls, group: ID, sender: ID, encoded_keys: Dict[str, str]) -> CustomizedContent:
        """ Update group keys from sender """
        return cls.create(action=cls.ACT_UPDATE, group=group, sender=sender, encoded_keys=encoded_keys)

    # 3. member -> bot: 'request'
    @classmethod
    def request_group_key(cls, group: ID, sender: ID, digest: str = None) -> CustomizedContent:
        """ Request group key for this member """
        return cls.create(action=cls.ACT_REQUEST, group=group, sender=sender, digest=digest)

    # 4. bot -> member: 'respond'
    @classmethod
    def respond_group_key(cls, group: ID, sender: ID, member: ID, encoded_key: str, digest: str) -> CustomizedContent:
        """ Respond group key to member """
        return cls.create(action=cls.ACT_RESPOND, group=group, sender=sender, encoded_keys={
            'digest': digest,
            str(member): encoded_key,
        })
