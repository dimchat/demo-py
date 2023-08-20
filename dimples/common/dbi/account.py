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
from typing import Optional, Union, Any, List, Dict

from dimsdk import PrivateKey, SignKey, DecryptKey
from dimsdk import ID, Meta, Document


class PrivateKeyDBI(ABC):
    """ PrivateKey Table """

    @abstractmethod
    def save_private_key(self, key: PrivateKey, user: ID, key_type: str = 'M') -> bool:
        raise NotImplemented

    @abstractmethod
    def private_keys_for_decryption(self, user: ID) -> List[DecryptKey]:
        raise NotImplemented

    @abstractmethod
    def private_key_for_signature(self, user: ID) -> Optional[SignKey]:
        raise NotImplemented

    @abstractmethod
    def private_key_for_visa_signature(self, user: ID) -> Optional[SignKey]:
        raise NotImplemented

    #
    #  Conveniences
    #

    @classmethod
    def convert_decrypt_keys(cls, keys: List[PrivateKey]) -> List[DecryptKey]:
        decrypt_keys = []
        for item in keys:
            if isinstance(item, DecryptKey):
                decrypt_keys.append(item)
        return decrypt_keys

    @classmethod
    def convert_private_keys(cls, keys: List[DecryptKey]) -> List[PrivateKey]:
        private_keys = []
        for item in keys:
            if isinstance(item, PrivateKey):
                private_keys.append(item)
        return private_keys

    @classmethod
    def revert_private_keys(cls, keys: List[PrivateKey]) -> List[Dict[str, Any]]:
        array = []
        for item in keys:
            array.append(item.dictionary)
        return array

    @classmethod
    def insert(cls, item: PrivateKey, array: List[PrivateKey]) -> Optional[List[PrivateKey]]:
        index = cls.find(item=item, array=array)
        if index == 0:
            # nothing changed
            return None
        elif index > 0:
            # move to the front
            array.pop(index)
        elif len(array) > 2:
            # keep only last three records
            array.pop()
        array.insert(0, item)
        return array

    @classmethod
    def find(cls, item: Union[DecryptKey, PrivateKey], array: List[PrivateKey]) -> int:
        index = 0
        data = item.get('data')
        for key in array:
            if key.get('data') == data:
                return index
            index += 1
        return -1


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
    """ User Table """

    @abstractmethod
    def contacts(self, user: ID) -> List[ID]:
        """ contacts for user """
        raise NotImplemented

    @abstractmethod
    def save_contacts(self, contacts: List[ID], user: ID) -> bool:
        raise NotImplemented


class GroupDBI(ABC):
    """ Group/Member Table """

    @abstractmethod
    def founder(self, group: ID) -> Optional[ID]:
        raise NotImplemented

    @abstractmethod
    def owner(self, group: ID) -> Optional[ID]:
        raise NotImplemented

    @abstractmethod
    def members(self, group: ID) -> List[ID]:
        raise NotImplemented

    @abstractmethod
    def save_members(self, members: List[ID], group: ID) -> bool:
        raise NotImplemented

    @abstractmethod
    def assistants(self, group: ID) -> List[ID]:
        raise NotImplemented

    @abstractmethod
    def save_assistants(self, assistants: List[ID], group: ID) -> bool:
        raise NotImplemented


# noinspection PyAbstractClass
class AccountDBI(PrivateKeyDBI, MetaDBI, DocumentDBI, UserDBI, GroupDBI, ABC):
    """ Account Database """
    pass
