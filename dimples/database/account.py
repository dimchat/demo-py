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

from typing import Optional, List, Tuple

from dimsdk import GroupCommand, ResetCommand
from dimsdk import PrivateKey, DecryptKey, SignKey
from dimsdk import ID, Meta, Document, Bulletin
from dimsdk import ReliableMessage

from ..common import AccountDBI

from .t_private import PrivateKeyTable
from .t_meta import MetaTable
from .t_document import DocumentTable
from .t_user import UserTable
from .t_group import GroupTable
from .t_group_history import GroupHistoryTable


class AccountDatabase(AccountDBI):
    """
        Database for MingKeMing
        ~~~~~~~~~~~~~~~~~~~~~~~
    """

    def __init__(self, root: str = None, public: str = None, private: str = None):
        super().__init__()
        self.__private_table = PrivateKeyTable(root=root, public=public, private=private)
        self.__meta_table = MetaTable(root=root, public=public, private=private)
        self.__doc_table = DocumentTable(root=root, public=public, private=private)
        self.__user_table = UserTable(root=root, public=public, private=private)
        self.__group_table = GroupTable(root=root, public=public, private=private)
        self.__history_table = GroupHistoryTable(root=root, public=public, private=private)

    def show_info(self):
        self.__private_table.show_info()
        self.__meta_table.show_info()
        self.__doc_table.show_info()
        self.__user_table.show_info()
        self.__group_table.show_info()
        self.__history_table.show_info()

    #
    #   PrivateKey DBI
    #

    # Override
    def save_private_key(self, key: PrivateKey, user: ID, key_type: str = 'M') -> bool:
        return self.__private_table.save_private_key(key=key, user=user, key_type=key_type)

    # Override
    def private_keys_for_decryption(self, user: ID) -> List[DecryptKey]:
        return self.__private_table.private_keys_for_decryption(user=user)

    # Override
    def private_key_for_signature(self, user: ID) -> Optional[SignKey]:
        return self.__private_table.private_key_for_signature(user=user)

    # Override
    def private_key_for_visa_signature(self, user: ID) -> Optional[SignKey]:
        return self.__private_table.private_key_for_visa_signature(user=user)

    #
    #   Meta DBI
    #

    # Override
    def save_meta(self, meta: Meta, identifier: ID) -> bool:
        # check meta with ID
        if not meta.match_identifier(identifier=identifier):
            raise ValueError('meta not match: %s => %s' % (identifier, meta))
        return self.__meta_table.save_meta(meta=meta, identifier=identifier)

    # Override
    def meta(self, identifier: ID) -> Optional[Meta]:
        return self.__meta_table.meta(identifier=identifier)

    #
    #   Document DBI
    #

    # Override
    def save_document(self, document: Document) -> bool:
        # check meta first
        meta = self.__meta_table.meta(identifier=document.identifier)
        if meta is None:
            raise LookupError('meta not exists: %s' % document.identifier)
        # check document valid before saving it
        if not (document.valid or document.verify(public_key=meta.public_key)):
            raise ValueError('document error: %s' % document.identifier)
        # check founder in group document
        if isinstance(document, Bulletin):
            founder = document.founder
            if founder is not None:
                f_meta = self.__meta_table.meta(identifier=founder)
                if f_meta is None or meta.public_key != meta.public_key:
                    raise ValueError('founder error: %s, group: %s' % (founder, document.identifier))
        # document ok, try to save it
        return self.__doc_table.save_document(document=document)

    # Override
    def documents(self, identifier: ID) -> List[Document]:
        return self.__doc_table.documents(identifier=identifier)

    #
    #   User DBI
    #

    # Override
    def local_users(self) -> List[ID]:
        return self.__user_table.local_users()

    # Override
    def save_local_users(self, users: List[ID]) -> bool:
        return self.__user_table.save_local_users(users=users)

    # Override
    def contacts(self, user: ID) -> List[ID]:
        return self.__user_table.contacts(user=user)

    # Override
    def save_contacts(self, contacts: List[ID], user: ID) -> bool:
        return self.__user_table.save_contacts(contacts=contacts, user=user)

    #
    #   Group DBI
    #

    # Override
    def founder(self, group: ID) -> Optional[ID]:
        return self.__group_table.founder(group=group)

    # Override
    def owner(self, group: ID) -> Optional[ID]:
        return self.__group_table.owner(group=group)

    # Override
    def members(self, group: ID) -> List[ID]:
        return self.__group_table.members(group=group)

    # Override
    def save_members(self, members: List[ID], group: ID) -> bool:
        return self.__group_table.save_members(members=members, group=group)

    # Override
    def assistants(self, group: ID) -> List[ID]:
        return self.__group_table.assistants(group=group)

    # Override
    def save_assistants(self, assistants: List[ID], group: ID) -> bool:
        return self.__group_table.save_assistants(assistants=assistants, group=group)

    # Override
    def administrators(self, group: ID) -> List[ID]:
        return self.__group_table.administrators(group=group)

    # Override
    def save_administrators(self, administrators: List[ID], group: ID) -> bool:
        return self.__group_table.save_administrators(administrators=administrators, group=group)

    #
    #   Group History DBI
    #

    # Override
    def save_group_history(self, group: ID, content: GroupCommand, message: ReliableMessage) -> bool:
        return self.__history_table.save_group_history(group=group, content=content, message=message)

    # Override
    def group_histories(self, group: ID) -> List[Tuple[GroupCommand, ReliableMessage]]:
        return self.__history_table.group_histories(group=group)

    # Override
    def reset_command_message(self, group: ID) -> Tuple[Optional[ResetCommand], Optional[ReliableMessage]]:
        return self.__history_table.reset_command_message(group=group)

    # Override
    def clear_group_member_histories(self, group: ID) -> bool:
        return self.__history_table.clear_group_member_histories(group=group)

    # Override
    def clear_group_admin_histories(self, group: ID) -> bool:
        return self.__history_table.clear_group_admin_histories(group=group)
