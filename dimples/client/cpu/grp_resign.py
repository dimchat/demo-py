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
from ...common import CommonFacebook

from .history import GroupCommandProcessor


class ResignCommandProcessor(GroupCommandProcessor):

    # Override
    def process_content(self, content: Content, r_msg: ReliableMessage) -> List[Content]:
        assert isinstance(content, ResignCommand), 'resign command error: %s' % content
        group = content.group
        # 0. check command
        if self._is_command_expired(command=content):
            # ignore expired command
            return []
        # 1. check group
        owner = self.group_owner(group=group)
        members = self.group_members(group=group)
        if owner is None or len(members) == 0:
            # TODO: query group members?
            return self._respond_receipt(text='Group empty.', msg=r_msg, group=group, extra={
                'template': 'Group empty: ${ID}',
                'replacements': {
                    'ID': str(group),
                }
            })
        sender = r_msg.sender
        administrators = self.group_administrators(group=group)
        # 2. do resign
        administrators = administrators.copy()
        sender_is_admin = sender in administrators
        if sender_is_admin:
            # admin do exist, remove it and update database
            administrators.remove(sender)
            self.save_administrators(administrators=administrators, group=group)
        # 3. update bulletin property: 'administrators'
        user = self.facebook.current_user
        assert user is not None, 'failed to get current user'
        me = user.identifier
        if me == owner:
            # maybe the bulletin in the owner's storage not contains this administrator,
            # but if it can still receive a resign command here, then
            # the owner should update the bulletin and send it out again.
            self.__refresh_administrators(group=group, owner=owner, administrators=administrators)
        else:
            # add 'resign' application for waiting owner to update
            self._add_application(command=content, message=r_msg)
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
        # 1. update bulletin
        bulletin = update_administrators(group=group, owner=owner, administrators=administrators, facebook=facebook)
        if not facebook.save_document(document=bulletin):
            return False
        meta = facebook.meta(identifier=group)
        command = DocumentCommand.response(document=bulletin, meta=meta, identifier=group)
        # 2. sent to assistants
        assistants = facebook.assistants(identifier=group)
        messenger = self.messenger
        for bot in assistants:
            assert bot != owner, 'group bot should not be owner: %s, %s, group: %s' % (owner, bot, group)
            messenger.send_content(sender=owner, receiver=bot, content=command, priority=1)


def update_administrators(group: ID, owner: ID, administrators: List[ID], facebook: CommonFacebook) -> Bulletin:
    # update document property
    bulletin = facebook.document(identifier=group)
    assert isinstance(bulletin, Bulletin), 'group document error: %s => %s' % (group, bulletin)
    bulletin.set_property(key='administrators', value=ID.revert(array=administrators))
    # sign document
    sign_key = facebook.private_key_for_visa_signature(identifier=owner)
    signature = bulletin.sign(private_key=sign_key)
    assert signature is not None, 'failed to sign bulletin for group: %s' % group
    return bulletin
