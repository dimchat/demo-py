# -*- coding: utf-8 -*-
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

from dimsdk import utf8_encode, base64_encode
from dimsdk import sha256
from dimsdk import SymmetricKey
from dimplugins import PlainKey


class Password:

    KEY_SIZE = 32

    BLOCK_SIZE = 16

    @classmethod
    def generate(cls, passphrase: str) -> SymmetricKey:
        data = utf8_encode(string=passphrase)
        digest = sha256(data=data)
        # AES key data
        filling = cls.KEY_SIZE - len(data)
        if filling > 0:
            # format: {digest_prefix}+{pwd_data}
            data = digest[0:filling] + data
        elif filling < 0:
            if cls.KEY_SIZE == len(digest):
                data = digest
            else:
                # FIXME: what about KEY_SIZE > len(digest)?
                data = digest[0:cls.KEY_SIZE]
        # pos = len(digest) - cls.BLOCK_SIZE
        # iv = digest[pos:]
        info = {
            'algorithm': SymmetricKey.AES,
            'data': base64_encode(data=data),
            # 'iv': base64_encode(iv),
        }
        return SymmetricKey.parse(key=info)

    """
        Plain Key
        ~~~~~~~~~
    """

    PLAIN = PlainKey.PLAIN

    kPlainKey = PlainKey()
