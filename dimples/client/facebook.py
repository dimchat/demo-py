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

from typing import Optional, List

from dimsdk import EntityType
from dimsdk import ID, Document, Bulletin
from dimsdk import BroadcastHelper

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
                ok = self.save_administrators(administrators=admins, group=group)
        return ok

    #
    #   GroupDataSource
    #

    # Override
    def founder(self, identifier: ID) -> Optional[ID]:
        # check broadcast group
        if identifier.is_broadcast:
            # founder of broadcast group
            return BroadcastHelper.broadcast_founder(group=identifier)
        # check bulletin document
        doc = self.bulletin(identifier=identifier)
        if doc is None:
            # the owner(founder) should be set in the bulletin document of group
            return None
        db = self.archivist
        # check local storage
        user = db.founder(identifier=identifier)
        if user is not None:
            # got from local storage
            return user
        # get from bulletin document
        user = doc.founder
        if user is None:
            self.error(msg='founder not designated for group: %s' % identifier)
        return user

    # Override
    def owner(self, identifier: ID) -> Optional[ID]:
        # check broadcast group
        if identifier.is_broadcast:
            # owner of broadcast group
            return BroadcastHelper.broadcast_owner(group=identifier)
        # check bulletin document
        doc = self.bulletin(identifier=identifier)
        if doc is None:
            # the owner(founder) should be set in the bulletin document of group
            return None
        db = self.archivist
        # check local storage
        user = db.owner(identifier=identifier)
        if user is not None:
            # got from local storage
            return user
        # check group type
        if identifier.type == EntityType.GROUP:
            # Polylogue's owner is its founder
            user = db.founder(identifier=identifier)
            if user is None:
                user = doc.founder
        if user is None:
            self.error(msg='owner not found for group: %s' % identifier)
        return user

    # Override
    def members(self, identifier: ID) -> List[ID]:
        owner = self.owner(identifier=identifier)
        if owner is None:
            self.error(msg='group empty: %s' % identifier)
            return []
        db = self.archivist
        # check local storage
        users = db.members(identifier=identifier)
        db.check_members(group=identifier, members=users)
        if len(users) == 0:
            users = [owner]
        else:
            assert users[0] == owner, 'group owner must be the first member: %s' % identifier
        return users

    # Override
    def assistants(self, identifier: ID) -> List[ID]:
        # check bulletin document
        doc = self.bulletin(identifier=identifier)
        if doc is None:
            # the assistants should be set in the bulletin document of group
            return []
        db = self.archivist
        # check local storage
        bots = db.assistants(identifier=identifier)
        if len(bots) > 0:
            # got from local storage
            return bots
        # get from bulletin document
        bots = doc.assistants
        return [] if bots is None else bots

    #
    #   Organizational Structure
    #

    def administrators(self, group: ID) -> List[ID]:
        # check bulletin document
        doc = self.bulletin(identifier=group)
        if doc is None:
            # the administrators should be set in the bulletin document
            return []
        db = self.archivist
        # the 'administrators' should be saved into local storage
        # when the newest bulletin document received,
        # so we must get them from the local storage only,
        # not from the bulletin document.
        return db.administrators(group=group)

    # protected
    def save_administrators(self, administrators: List[ID], group: ID) -> bool:
        db = self.archivist
        return db.save_administrators(administrators, group=group)

    # protected
    def save_members(self, members: List[ID], group: ID) -> bool:
        db = self.archivist
        return db.save_members(members, group=group)


# TODO: ANS?
