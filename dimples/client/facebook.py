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
    Facebook for client
    ~~~~~~~~~~~~~~~~~~~

    Barrack for cache entities
"""

from typing import List

from dimsdk import ID, Document, Bulletin

from ..common import CommonFacebook


class ClientFacebook(CommonFacebook):

    # Override
    def save_document(self, document: Document) -> bool:
        ok = super().save_document(document=document)
        if ok and isinstance(document, Bulletin):
            # check administrators
            array = document.get_property(key='administrators')
            if array is not None:
                group = document.identifier
                assert group.is_group, 'group ID error: %s' % group
                admins = ID.convert(array=array)
                ok = self._save_administrators(administrators=admins, group=group)
        return ok

    def _save_administrators(self, administrators: List[ID], group: ID) -> bool:
        db = self.database
        return db.save_administrators(administrators=administrators, group=group)


# TODO: ANS?
