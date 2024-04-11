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

from abc import ABC
from typing import List

from dimsdk import DateTime
from dimsdk import Content
from dimsdk import ReliableMessage
from dimsdk import MessageProcessor

from ..utils import Logging

from .archivist import CommonArchivist


# noinspection PyAbstractClass
class CommonMessageProcessor(MessageProcessor, Logging, ABC):

    # private
    # noinspection PyUnusedLocal
    def _check_visa_time(self, content: Content, r_msg: ReliableMessage) -> bool:
        facebook = self.facebook
        archivist = facebook.archivist
        assert isinstance(archivist, CommonArchivist), 'archivist error: %s' % archivist
        doc_updated = False
        # check sender document time
        last_doc_time = r_msg.get_datetime(key='SDT', default=None)
        if last_doc_time is not None:
            now = DateTime.now()
            if last_doc_time.after(now):
                # calibrate the clock
                last_doc_time = now
            sender = r_msg.sender
            doc_updated = archivist.set_last_document_time(identifier=sender, last_time=last_doc_time)
            # check whether needs update
            if doc_updated:
                self.info(msg='checking for new visa: %s' % sender)
                facebook.documents(identifier=sender)
        return doc_updated

    # Override
    def process_content(self, content: Content, r_msg: ReliableMessage) -> List[Content]:
        responses = super().process_content(content=content, r_msg=r_msg)
        # check sender's document times from the message
        # to make sure the user info synchronized
        self._check_visa_time(content=content, r_msg=r_msg)
        return responses
