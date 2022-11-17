# -*- coding: utf-8 -*-
#
#   DIMP : Decentralized Instant Messaging Protocol
#
#                                Written in 2019 by Moky <albert.moky@gmail.com>
#
# ==============================================================================
# MIT License
#
# Copyright (c) 2019 Albert Moky
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
    Receipt Protocol
    ~~~~~~~~~~~~~~~~

    As receipt returned to sender to proofing the message's received
"""

from typing import Optional, Union, Any, Dict

from dimsdk import Envelope, ReliableMessage
from dimsdk import BaseCommand

from ...utils import base64_encode


class ReceiptCommand(BaseCommand):
    """
        Receipt Command
        ~~~~~~~~~~~~~~~

        data format: {
            type : 0x88,
            sn   : 456,

            cmd    : "receipt",
            text   : "...",  // text message
            origin : {         // original message envelope
                sender    : "...",
                receiver  : "...",
                time      : 0,
                sn        : 123,
                signature : "..."
            }
        }
    """
    RECEIPT = 'receipt'

    def __init__(self, content: Dict[str, Any] = None, text: str = None,
                 envelope: Envelope = None, sn: int = 0, signature: Union[str, bytes] = None):
        if content is None:
            # create with text
            # create with envelope, sn, signature
            super().__init__(cmd=self.RECEIPT)
            # text message
            if text is not None:
                self['text'] = text
            self.__envelope = envelope
            # envelope of the message responding to
            if envelope is None:
                origin = {}
            else:
                origin = envelope.dictionary
            # sn of the message responding to
            if sn > 0:
                origin['sn'] = sn
            # signature of the message responding to
            if isinstance(signature, str):
                origin['signature'] = signature
            elif isinstance(signature, bytes):
                origin['signature'] = base64_encode(data=signature)
            if len(origin) > 0:
                self['origin'] = origin
        else:
            # create with command content
            super().__init__(content=content)
            # lazy load
            self.__envelope = None

    # -------- setters/getters

    @property
    def text(self) -> Optional[str]:
        return self.get('text')

    @property  # private
    def origin(self) -> dict:
        return self.get('origin')

    @property
    def original_envelope(self) -> Optional[Envelope]:
        if self.__envelope is None:
            # origin: { sender: "...", receiver: "...", time: 0 }
            origin = self.origin
            if origin is not None and 'sender' in origin:
                self.__envelope = Envelope.parse(envelope=origin)
        return self.__envelope

    @property
    def original_sn(self) -> int:
        origin = self.origin
        return 0 if origin is None else origin.get('sn')

    @property
    def original_signature(self) -> Optional[str]:
        origin = self.origin
        return None if origin is None else origin.get('signature')

    #
    #   Factory method
    #

    @classmethod
    def create(cls, text: str = None, msg: ReliableMessage = None):
        """
        Create receipt with text message and origin message envelope

        :param text: text message
        :param msg:  origin message
        :return: ReceiptCommand
        """
        if msg is None:
            assert text is not None, 'cannot create empty receipt command'
            envelope = None
        else:
            ignores = ['data', 'key', 'keys', 'meta', 'visa']
            env = {}
            info = msg.dictionary
            for key in info:
                if key not in ignores:
                    env[key] = info[key]
            assert 'sender' in env, 'message envelope error: %s' % env
            envelope = Envelope.parse(envelope=env)
        return cls(text=text, envelope=envelope)
