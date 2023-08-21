# -*- coding: utf-8 -*-
#
#   DIM-SDK : Decentralized Instant Messaging Software Development Kit
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
    Resign Group Admin Command Processor
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    1. resign the group administrator
    3. administrator can be hired/fired by owner only
"""

from typing import List

from dimsdk import ID, Bulletin
from dimsdk import ReliableMessage
from dimsdk import Content
from dimsdk import DocumentCommand

from ...common.protocol import ResignCommand

from .history import GroupCommandProcessor


class ResignCommandProcessor(GroupCommandProcessor):

    # Override
    def process_content(self, content: Content, r_msg: ReliableMessage) -> List[Content]:
        assert isinstance(content, ResignCommand), 'resign command error: %s' % content
        group = content.group
        # 1. check group
        owner = self.group_owner(group=group)
        members = self.group_members(group=group)
        if owner is None or len(members) == 0:
            return self._respond_receipt(text='Group empty.', msg=r_msg, group=group, extra={
                'template': 'Group empty: ${ID}',
                'replacements': {
                    'ID': str(group),
                }
            })
        administrators = self.group_administrators(group=group)
        # 2. update database
        sender = r_msg.sender
        sender_is_admin = sender in administrators
        if sender_is_admin:
            # admin do exist, remove it and update database
            administrators.remove(sender)
            self.save_administrators(administrators=administrators, group=group)
        # 3. update bulletin
        user = self.facebook.current_user
        if user.identifier == owner:
            # maybe the bulletin in the owner's storage not contains this administrator,
            # but if it can still receive a resign command here, then
            # the owner should update the bulletin and send it out again.
            self.__refresh_administrators(group=group, owner=owner, administrators=administrators)
        if not sender_is_admin:
            return self._respond_receipt(text='Permission denied.', msg=r_msg, group=group, extra={
                'template': 'Not an administrator of group: ${ID}',
                'replacements': {
                    'ID': str(group),
                }
            })
        # no need to response this group command
        return []

    def __refresh_administrators(self, group: ID, owner: ID, administrators: List[ID]):
        facebook = self.facebook
        sign_key = facebook.private_key_for_visa_signature(identifier=owner)
        # 1. update bulletin
        meta = facebook.meta(identifier=group)
        bulletin = facebook.document(identifier=group)
        assert isinstance(bulletin, Bulletin), 'group document error: %s => %s' % (group, bulletin)
        bulletin.set_property(key='administrators', value=ID.revert(array=administrators))
        bulletin.sign(private_key=sign_key)
        facebook.save_document(document=bulletin)
        # 2. sent to assistants
        command = DocumentCommand.response(document=bulletin, meta=meta, identifier=group)
        assistants = facebook.assistants(identifier=group)
        messenger = self.messenger
        for bot in assistants:
            messenger.send_content(sender=owner, receiver=bot, content=command, priority=1)
