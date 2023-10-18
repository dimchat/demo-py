# -*- coding: utf-8 -*-
#
#   DIM-SDK : Decentralized Instant Messaging Software Development Kit
#
#                                Written in 2023 by Moky <albert.moky@gmail.com>
#
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

from typing import List

from dimsdk import ID, Bulletin
from dimsdk import Station
from dimsdk import DocumentCommand

from ..utils import Logging
from ..common import CommonFacebook, CommonMessenger

from .delegate import GroupDelegate


class AdminManager(Logging):

    def __init__(self, delegate: GroupDelegate):
        super().__init__()
        self.__delegate = delegate

    @property  # protected
    def delegate(self) -> GroupDelegate:
        return self.__delegate

    @property  # protected
    def facebook(self) -> CommonFacebook:
        return self.delegate.facebook

    @property  # protected
    def messenger(self) -> CommonMessenger:
        return self.delegate.messenger

    def update_administrators(self, administrators: List[ID], group: ID) -> bool:
        """
        Update 'administrators' in bulletin document
        (broadcast new document to all members and neighbor station)

        :param administrators: admin list
        :param group:          group ID
        :return: False on error
        """
        assert group.is_group, 'group ID error: %s' % group
        facebook = self.facebook
        delegate = self.delegate
        #
        #   0. get current user
        #
        user = facebook.current_user
        if user is None:
            self.error(msg='failed to get current user')
            return False
        me = user.identifier
        sign_key = facebook.private_key_for_visa_signature(identifier=me)
        assert sign_key is not None, 'failed to get sign key for current user: %s' % me
        #
        #   1. check permission
        #
        is_owner = delegate.is_owner(user=me, group=group)
        if not is_owner:
            self.warning(msg='cannot update administrators for group: %s, %s' % (group, me))
            return False
        #
        #   2. update document
        #
        doc = delegate.document(identifier=group)
        if doc is None:
            # TODO: create new one?
            self.error(msg='failed to get group document: %s, owner: %s' % (group, me))
            return False
        doc.set_property(key='administrators', value=ID.revert(array=administrators))
        signature = None if sign_key is None else doc.sign(private_key=sign_key)
        if signature is None:
            self.error(msg='failed to sign document for group: %s, owner: %s' % (group, me))
            return False
        elif not delegate.save_document(document=doc):
            self.error(msg='failed to save document for group: %s' % group)
            return False
        else:
            self.info(msg='group document updated: %s' % group)
        #
        #   3. broadcast bulletin document
        #
        assert isinstance(doc, Bulletin), 'group document error: %s' % doc
        return self.broadcast_document(document=doc)

    def broadcast_document(self, document: Bulletin) -> bool:
        facebook = self.facebook
        messenger = self.messenger
        assert facebook is not None and messenger is not None,\
            'facebook messenger not ready: %s, %s' % (facebook, messenger)
        delegate = self.delegate
        #
        #   0. get current user
        #
        user = facebook.current_user
        if user is None:
            self.error(msg='failed to get current user')
            return False
        me = user.identifier
        #
        #   1. create 'document' command, and send to current station
        #
        group = document.identifier
        meta = facebook.meta(identifier=group)
        content = DocumentCommand.response(identifier=group, meta=meta, document=document)
        messenger.send_content(sender=me, receiver=Station.ANY, content=content, priority=1)
        #
        #   2. check group bots
        #
        bots = delegate.assistants(identifier=group)
        if len(bots) > 0:
            # group bots exist, let them to deliver to all other members
            for item in bots:
                if me == item:
                    self.info(msg='skip cycled message: %s' % item)
                    continue
                messenger.send_content(sender=me, receiver=item, content=content, priority=1)
            return True
        #
        #   3. broadcast to all members
        #
        members = delegate.members(identifier=group)
        if len(members) == 0:
            self.error(msg='failed to get group members: %s' % group)
            return False
        for item in members:
            if me == item:
                self.info(msg='skip cycled message: %s' % item)
                continue
            messenger.send_content(sender=me, receiver=item, content=content, priority=1)
        return True
