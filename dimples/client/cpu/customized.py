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

from abc import ABC, abstractmethod
from typing import Optional, List, Dict

from dimsdk import ID
from dimsdk import ReliableMessage
from dimsdk import Envelope
from dimsdk import ContentType, Content
from dimsdk import ReceiptCommand
from dimsdk import GroupCommand, QueryCommand
from dimsdk import TwinsHelper
from dimsdk import Facebook, Messenger
from dimsdk.cpu import BaseContentProcessor

from ...common import CustomizedContent
from ...common import GroupHistory


class CustomizedContentHandler(ABC):
    """
        Handler for Customized Content
        ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    """

    @abstractmethod
    async def handle_action(self, act: str, sender: ID, content: CustomizedContent,
                            msg: ReliableMessage) -> List[Content]:
        """
        Do your job

        @param act:     action
        @param sender:  user ID
        @param content: customized content
        @param msg:     network message
        @return contents
        """
        raise NotImplemented


class BaseCustomizedHandler(TwinsHelper, CustomizedContentHandler):
    """
        Default Handler
        ~~~~~~~~~~~~~~~
    """

    # Override
    async def handle_action(self, act: str, sender: ID, content: CustomizedContent,
                            msg: ReliableMessage) -> List[Content]:
        app = content.application
        mod = content.module
        text = 'Content not support.'
        return self._respond_receipt(text=text, content=content, envelope=msg.envelope, extra={
            'template': 'Customized content (app: ${app}, mod: ${mod}, act: ${act}) not support yet!',
            'replacements': {
                'app': app,
                'mod': mod,
                'act': act,
            }
        })

    #
    #   Convenient responding
    #

    # noinspection PyMethodMayBeStatic
    def _respond_receipt(self, text: str, envelope: Envelope, content: Optional[Content],
                         extra: Optional[Dict] = None) -> List[ReceiptCommand]:
        return [
            # create base receipt command with text & original envelope
            BaseContentProcessor.create_receipt(text=text, envelope=envelope, content=content, extra=extra)
        ]


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


class CustomizedContentProcessor(BaseContentProcessor):
    """
        Customized Content Processing Unit
        ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
        Handle content for application customized
    """

    def __init__(self, facebook: Facebook, messenger: Messenger):
        super().__init__(facebook=facebook, messenger=messenger)
        self.__default_handler = self._create_default_handler(facebook=facebook, messenger=messenger)
        self.__group_history_handler = self._create_group_history_handler(facebook=facebook, messenger=messenger)

    # noinspection PyMethodMayBeStatic
    def _create_default_handler(self, facebook: Facebook, messenger: Messenger) -> CustomizedContentHandler:
        return BaseCustomizedHandler(facebook=facebook, messenger=messenger)

    # noinspection PyMethodMayBeStatic
    def _create_group_history_handler(self, facebook: Facebook, messenger: Messenger) -> GroupHistoryHandler:
        return GroupHistoryHandler(facebook=facebook, messenger=messenger)

    @property  # protected
    def default_handler(self) -> CustomizedContentHandler:
        return self.__default_handler

    @property  # protected
    def group_history_handler(self) -> GroupHistoryHandler:
        return self.__group_history_handler

    # Override
    async def process_content(self, content: Content, r_msg: ReliableMessage) -> List[Content]:
        assert isinstance(content, CustomizedContent), 'customized content error: %s' % content
        # get handler for 'app' & 'mod'
        app = content.application
        mod = content.module
        handler = self._filter(app, mod, content=content, msg=r_msg)
        if handler is None:
            # module not support
            handler = self.default_handler
        # handle the action
        act = content.action
        sender = r_msg.sender
        return await handler.handle_action(act, sender=sender, content=content, msg=r_msg)

    # noinspection PyUnusedLocal
    def _filter(self, app: str, mod: str,
                content: CustomizedContent, msg: ReliableMessage) -> Optional[CustomizedContentHandler]:
        """ Override for your handler """
        if content.group is not None:
            handler = self.group_history_handler
            if handler.matches(app=app, mod=mod):
                return handler
        # if the application has too many modules, I suggest you to
        # use different handler to do the job for each module.
        return None
