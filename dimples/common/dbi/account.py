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

from abc import ABC, abstractmethod
from typing import Optional, List

from dimsdk import PrivateKey, SignKey, DecryptKey
from dimsdk import ID, Meta, Document
from dimsdk import GroupDataSource


class PrivateKeyDBI(ABC):
    """ PrivateKey Table """

    @abstractmethod
    def save_private_key(self, key: PrivateKey, identifier: ID, key_type: str = 'M') -> bool:
        raise NotImplemented

    @abstractmethod
    def private_keys_for_decryption(self, identifier: ID) -> List[DecryptKey]:
        raise NotImplemented

    @abstractmethod
    def private_key_for_signature(self, identifier: ID) -> Optional[SignKey]:
        raise NotImplemented

    @abstractmethod
    def private_key_for_visa_signature(self, identifier: ID) -> Optional[SignKey]:
        raise NotImplemented


class MetaDBI(ABC):
    """ Meta Table """

    @abstractmethod
    def save_meta(self, meta: Meta, identifier: ID) -> bool:
        raise NotImplemented

    @abstractmethod
    def meta(self, identifier: ID) -> Optional[Meta]:
        raise NotImplemented


class DocumentDBI(ABC):
    """ Document Table """

    @abstractmethod
    def save_document(self, document: Document) -> bool:
        raise NotImplemented

    @abstractmethod
    def document(self, identifier: ID, doc_type: str = '*') -> Optional[Document]:
        raise NotImplemented


class UserDBI(ABC):
    """ User/Contact Table """

    @abstractmethod
    def local_users(self) -> List[ID]:
        raise NotImplemented

    @abstractmethod
    def contacts(self, identifier: ID) -> List[ID]:
        """ contacts for user """
        raise NotImplemented


class GroupDBI(GroupDataSource, ABC):
    """ Group/Member Table """

    @abstractmethod
    def save_members(self, members: List[ID], identifier: ID) -> bool:
        raise NotImplemented

    @abstractmethod
    def save_assistants(self, assistants: List[ID], identifier: ID) -> bool:
        raise NotImplemented


class AccountDBI(PrivateKeyDBI, MetaDBI, DocumentDBI, UserDBI, GroupDBI, ABC):
    """ Account Database """
    pass
