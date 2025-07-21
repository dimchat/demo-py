# -*- coding: utf-8 -*-
#
#   DIM-SDK : Decentralized Instant Messaging Software Development Kit
#
#                                Written in 2022 by Moky <albert.moky@gmail.com>
#
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
from dimsdk import ContentType, Content
from dimsdk import CustomizedContent
from dimsdk import GroupCommand, QueryCommand
from dimsdk import Facebook, Messenger
from dimsdk.cpu import CustomizedContentHandler, BaseCustomizedHandler
from dimsdk.cpu import CustomizedContentProcessor

from ...common import GroupHistory


class GroupHistoryHandler(BaseCustomizedHandler):
    """ Command Transform:

        +===============================+===============================+
        |      Customized Content       |      Group Query Command      |
        +-------------------------------+-------------------------------+
        |   "type" : i2s(0xCC)          |   "type" : i2s(0x88)          |
        |   "sn"   : 123                |   "sn"   : 123                |
        |   "time" : 123.456            |   "time" : 123.456            |
        |   "app"  : "chat.dim.group"   |                               |
        |   "mod"  : "history"          |                               |
        |   "act"  : "query"            |                               |
        |                               |   "command"   : "query"       |
        |   "group"     : "{GROUP_ID}"  |   "group"     : "{GROUP_ID}"  |
        |   "last_time" : 0             |   "last_time" : 0             |
        +===============================+===============================+
    """

    # noinspection PyMethodMayBeStatic
    def matches(self, app: str, mod: str) -> bool:
        return app == GroupHistory.APP and mod == GroupHistory.MOD

    # Override
    async def handle_action(self, act: str, sender: ID, content: CustomizedContent,
                            msg: ReliableMessage) -> List[Content]:
        messenger = self.messenger
        if messenger is None:
            assert False, 'messenger lost'
            # return []
        elif act == GroupHistory.ACT_QUERY:
            assert GroupHistory.APP == content.application
            assert GroupHistory.MOD == content.module
            assert content.group is not None, 'group command error: %s, sender: %s' % (content, sender)
        else:
            # assert False, 'unknown action: %s, %s, sender: %s' % (act, content, sender)
            return await super().handle_action(act=act, sender=sender, content=content, msg=msg)
        info = content.copy_dictionary()
        info['type'] = ContentType.COMMAND
        info['command'] = GroupCommand.QUERY
        query = Content.parse(content=info)
        if isinstance(query, QueryCommand):
            return await messenger.process_content(content=query, r_msg=msg)
        # else:
        #     assert False, 'query command error: %s, %s, sender: %s' % (query, content, sender)
        text = 'Query command error.'
        return self._respond_receipt(text=text, envelope=msg.envelope, content=content)


class AppCustomizedContentProcessor(CustomizedContentProcessor):
    """
        Customized Content Processing Unit
        ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
        Handle content for application customized
    """

    def __init__(self, facebook: Facebook, messenger: Messenger):
        super().__init__(facebook=facebook, messenger=messenger)
        self.__group_history_handler = self._create_group_history_handler(facebook=facebook, messenger=messenger)

    # noinspection PyMethodMayBeStatic
    def _create_group_history_handler(self, facebook: Facebook, messenger: Messenger) -> GroupHistoryHandler:
        return GroupHistoryHandler(facebook=facebook, messenger=messenger)

    @property  # protected
    def group_history_handler(self) -> GroupHistoryHandler:
        return self.__group_history_handler

    # noinspection PyUnusedLocal
    def _filter(self, app: str, mod: str, content: CustomizedContent, msg: ReliableMessage) -> CustomizedContentHandler:
        """ Override for your handler """
        if content.group is not None:
            handler = self.group_history_handler
            if handler.matches(app=app, mod=mod):
                return handler
        # default handler
        return super()._filter(app=app, mod=mod, content=content, msg=msg)
