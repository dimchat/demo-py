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
from typing import Optional, List

from dimsdk import ID
from dimsdk import ReliableMessage
from dimsdk import Content
from dimsdk.cpu import BaseContentProcessor

from ...common import CustomizedContent


class CustomizedContentHandler(ABC):
    """
        Handler for Customized Content
        ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    """

    @abstractmethod
    async def handle_action(self, act: str, sender: ID,
                            content: CustomizedContent, msg: ReliableMessage) -> List[Content]:
        """
        Do your job

        @param act:     action
        @param sender:  user ID
        @param content: customized content
        @param msg:     network message
        @return contents
        """
        raise NotImplemented


class CustomizedContentProcessor(BaseContentProcessor, CustomizedContentHandler):
    """
        Customized Content Processing Unit
        ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    """

    # Override
    async def process_content(self, content: Content, r_msg: ReliableMessage) -> List[Content]:
        assert isinstance(content, CustomizedContent), 'customized content error: %s' % content
        # 1. check app id
        app = content.application
        responses = self._filter(app, content=content, msg=r_msg)
        if responses is not None:
            # app id not found
            return responses
        # 2. get handler with module name
        mod = content.module
        handler = self._fetch(mod, content=content, msg=r_msg)
        if handler is None:
            # module not support
            return []
        # 3. do the job
        act = content.action
        sender = r_msg.sender
        return await handler.handle_action(act, sender=sender, content=content, msg=r_msg)

    # noinspection PyUnusedLocal
    def _filter(self, app: str, content: CustomizedContent, msg: ReliableMessage) -> Optional[List[Content]]:
        # Override for your application
        """
        Check for application

        :param app:     app ID
        :param content: customized content
        :param msg:     received message
        :return: None on app ID matched
        """
        text = 'Content not support.'
        return self._respond_receipt(text=text, content=content, envelope=msg.envelope, extra={
            'template': 'Customized content (app: ${app}) not support yet!',
            'replacements': {
                'app': app,
            }
        })

    # noinspection PyUnusedLocal
    def _fetch(self, mod: str, content: CustomizedContent, msg: ReliableMessage) -> Optional[CustomizedContentHandler]:
        """ Override for you module """
        # if the application has too many modules, I suggest you to
        # use different handler to do the job for each module.
        return self

    # Override
    async def handle_action(self, act: str, sender: ID,
                            content: CustomizedContent, msg: ReliableMessage) -> List[Content]:
        """ Override for customized actions """
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
