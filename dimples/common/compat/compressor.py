# -*- coding: utf-8 -*-
# ==============================================================================
# MIT License
#
# Copyright (c) 2025 Albert Moky
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

from typing import Optional, Dict

from dimsdk import MessageCompressor
from dimsdk import MessageShortener

from .compatible import CompatibleIncoming


class CompatibleCompressor(MessageCompressor):

    # Override
    def _create_shortener(self) -> MessageShortener:
        return CompatibleShortener()

    # Override
    def compress_content(self, content: Dict, key: Dict) -> bytes:
        # CompatibleOutgoing.fix_content(content=content);
        return super().compress_content(content=content, key=key)

    # Override
    def extract_content(self, data: bytes, key: Dict) -> Optional[Dict]:
        content = super().extract_content(data=data, key=key)
        if content is not None:
            CompatibleIncoming.fix_content(content=content)
        return content


class CompatibleShortener(MessageShortener):

    # Override
    def compress_content(self, content: Dict) -> Dict:
        # DON'T COMPRESS NOW
        return content

    # Override
    def compress_symmetric_key(self, key: Dict) -> Dict:
        # DON'T COMPRESS NOW
        return key

    # Override
    def compress_reliable_message(self, msg: Dict) -> Dict:
        # DON'T COMPRESS NOW
        return msg
