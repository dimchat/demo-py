# -*- coding: utf-8 -*-
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

from typing import Optional

from dimsdk import ID, Document

from ...common import DocumentDBI

from .base import Storage
from .base import template_replace


class DocumentStorage(Storage, DocumentDBI):
    """
        Document for Entities (User/Group)
        ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
        file path: '.dim/public/{ADDRESS}/document.js'
    """
    doc_path = '{PUBLIC}/{ADDRESS}/document.js'

    def show_info(self):
        path = template_replace(self.doc_path, 'PUBLIC', self._public)
        print('!!!       document path: %s' % path)

    def __doc_path(self, identifier: ID) -> str:
        path = self.doc_path
        path = template_replace(path, 'PUBLIC', self._public)
        return template_replace(path, 'ADDRESS', str(identifier.address))

    #
    #   Document DBI
    #

    # Override
    def save_document(self, document: Document) -> bool:
        """ save document into file """
        path = self.__doc_path(identifier=document.identifier)
        self.info(msg='Saving document into: %s' % path)
        return self.write_json(container=document.dictionary, path=path)

    # Override
    def document(self, identifier: ID, doc_type: str = '*') -> Optional[Document]:
        """ load document from file """
        path = self.__doc_path(identifier=identifier)
        self.info(msg='Loading document from: %s' % path)
        info = self.read_json(path=path)
        if info is not None:
            return parse_document(dictionary=info, identifier=identifier, doc_type=doc_type)


def parse_document(dictionary: dict, identifier: ID = None, doc_type: str = '*') -> Optional[Document]:
    # check document ID
    doc_id = ID.parse(identifier=dictionary.get('ID'))
    assert doc_id is not None, 'document error: %s' % dictionary
    if identifier is None:
        identifier = doc_id
    else:
        assert identifier == doc_id, 'document ID not match: %s, %s' % (identifier, doc_id)
    # check document type
    doc_ty = dictionary.get('type')
    if doc_ty is not None:
        doc_type = doc_ty
    # check document data
    data = dictionary.get('data')
    if data is None:
        # compatible with v1.0
        data = dictionary.get('profile')
    # check document signature
    signature = dictionary.get('signature')
    if data is None or signature is None:
        raise ValueError('document error: %s' % dictionary)
    doc = Document.create(doc_type=doc_type, identifier=identifier, data=data, signature=signature)
    for key in dictionary:
        if key == 'ID' or key == 'data' or key == 'signature':
            continue
        doc[key] = dictionary[key]
    return doc
