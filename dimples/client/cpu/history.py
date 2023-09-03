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
    Group History Processors
    ~~~~~~~~~~~~~~~~~~~~~~~~

"""

from typing import Optional, List, Tuple

from dimsdk import EntityType, ID, ANYONE
from dimsdk import InstantMessage, ReliableMessage
from dimsdk import Envelope, Content, ForwardContent
from dimsdk import Command, GroupCommand
from dimsdk import ResetCommand, InviteCommand, JoinCommand, QuitCommand
from dimsdk import BaseCommandProcessor


from ...common.dbi import is_expired
from ...common.protocol import ResignCommand
from ...common import AccountDBI
from ...common import CommonFacebook, CommonMessenger


class HistoryCommandProcessor(BaseCommandProcessor):

    # Override
    def process_content(self, content: Content, r_msg: ReliableMessage) -> List[Content]:
        assert isinstance(content, Command), 'history command error: %s' % content
        return self._respond_receipt(text='Command not support.', msg=r_msg, group=content.group, extra={
            'template': 'History command (name: ${command}) not support yet!',
            'replacements': {
                'command': content.cmd,
            }
        })


class GroupCommandProcessor(HistoryCommandProcessor):

    @property
    def messenger(self) -> CommonMessenger:
        transceiver = super().messenger
        assert isinstance(transceiver, CommonMessenger), 'messenger error: %s' % transceiver
        return transceiver

    @property
    def facebook(self) -> CommonFacebook:
        barrack = super().facebook
        assert isinstance(barrack, CommonFacebook), 'facebook error: %s' % barrack
        return barrack

    def group_owner(self, group: ID) -> Optional[ID]:
        facebook = self.facebook
        return facebook.owner(identifier=group)

    def group_members(self, group: ID) -> List[ID]:
        facebook = self.facebook
        return facebook.members(identifier=group)

    def group_assistants(self, group: ID) -> List[ID]:
        facebook = self.facebook
        return facebook.assistants(identifier=group)

    def group_administrators(self, group: ID) -> List[ID]:
        db = self.facebook.database
        return db.administrators(group=group)

    def save_members(self, members: List[ID], group: ID) -> bool:
        db = self.facebook.database
        return db.save_members(members=members, group=group)

    def save_administrators(self, administrators: List[ID], group: ID) -> bool:
        db = self.facebook.database
        return db.save_administrators(administrators=administrators, group=group)

    @staticmethod
    def command_members(content: GroupCommand) -> List[ID]:
        # get from 'members'
        array = content.members
        if array is None:
            # get from 'member
            item = content.member
            if item is None:
                array = []
            else:
                array = [item]
        return array

    # Override
    def process_content(self, content: Content, r_msg: ReliableMessage) -> List[Content]:
        assert isinstance(content, GroupCommand), 'group command error: %s' % content
        return self._respond_receipt(text='Command not support.', msg=r_msg, group=content.group, extra={
            'template': 'Group command (name: ${command}) not support yet!',
            'replacements': {
                'command': content.cmd,
            }
        })

    def _is_command_expired(self, command: GroupCommand) -> bool:
        facebook = self.facebook
        group = command.group
        if isinstance(command, ResignCommand):
            # administrator command, check with document time
            bulletin = facebook.document(identifier=group)
            if bulletin is None:
                return False
            return is_expired(old_time=bulletin.time, new_time=command.time)
        # membership command, check with reset command
        db = facebook.database
        cmd, msg = db.reset_command_message(group=group)
        if cmd is None:  # or msg is None:
            return False
        return is_expired(old_time=cmd.time, new_time=command.time)

    def _add_application(self, command: GroupCommand, message: ReliableMessage):
        """ attach 'invite', 'join', 'quit' commands to 'reset' command message for owner/admins to review """
        # InviteCommand, JoinCommand, QuitCommand
        # ResignCommand
        assert isinstance(command, InviteCommand) \
            or isinstance(command, JoinCommand) \
            or isinstance(command, QuitCommand) \
            or isinstance(command, ResignCommand), 'group command error: %s' % command
        # TODO: attach 'resign' command to document?
        facebook = self.facebook
        group = command.group
        db = facebook.database
        cmd, msg = db.reset_command_message(group=group)
        if cmd is None or msg is None:
            user = facebook.current_user
            assert user is not None, 'failed to get current user'
            me = user.identifier
            # TODO: check whether current user is the owner or an administrator
            #       if True, create a new 'reset' command with current members
            assert me.type != EntityType.BOT, 'failed to get reset command for group: %s' % group
            return False
        applications = msg.get('applications')
        if isinstance(applications, List):
            applications.append(message.dictionary)
        else:
            msg['applications'] = [message.dictionary]
        return db.save_reset_command_message(group=group, content=cmd, msg=msg)

    def _send_reset_command(self, group: ID, members: List[ID], receiver: ID):
        """ send a reset command with newest members to the receiver """
        messenger = self.messenger
        facebook = self.facebook
        user = facebook.current_user
        assert user is not None, 'failed to get current user'
        me = user.identifier
        db = facebook.database
        _, msg = db.reset_command_message(group=group)
        if msg is None:
            # 'reset' command message not found in local storage,
            # check permission for creating a new one
            owner = self.group_owner(group=group)
            if me != owner:
                # not group owner, check administrators
                administrators = self.group_administrators(group=group)
                if me not in administrators:
                    # only group owner and administrators can reset group members
                    return False
            assert me.type != EntityType.BOT, 'a bot should not be group owner/administrator: %s, %s' % (me, group)
            # this is the group owner (or administrator), so
            # it has permission to reset group members here.
            cmd, msg = create_reset_command(sender=me, group=group, members=members, messenger=messenger)
            if not db.save_reset_command_message(group=group, content=cmd, msg=msg):
                # failed to save 'reset' command message
                return False
        # OK, forward the 'reset' command message
        content = ForwardContent.create(message=msg)
        messenger.send_content(sender=me, receiver=receiver, content=content, priority=1)
        return True


def create_reset_command(sender: ID, group: ID, members: List[ID],
                         messenger: CommonMessenger) -> Tuple[ResetCommand, ReliableMessage]:
    """ create 'reset' command message for anyone in the group """
    head = Envelope.create(sender=sender, receiver=ANYONE)
    body = GroupCommand.reset(group=group, members=members)
    i_msg = InstantMessage.create(head=head, body=body)
    # encrypt & sign
    s_msg = messenger.encrypt_message(msg=i_msg)
    assert s_msg is not None, 'failed to encrypt message: %s -> %s' % (sender, group)
    r_msg = messenger.sign_message(msg=s_msg)
    assert r_msg is not None, 'failed to sign message: %s -> %s' % (sender, group)
    return body, r_msg


def update_reset_command_message(group: ID, cmd: ResetCommand, msg: ReliableMessage, database: AccountDBI) -> bool:
    """ save 'reset' command message with 'applications' """
    # 1. get applications
    _, old = database.reset_command_message(group=group)
    applications = None if old is None else old.get('applications')
    if applications is None:
        applications = msg.get('applications')
    else:
        invitations = msg.get('applications')
        if invitations is not None:
            # assert isinstance(invitations, List), 'applications error: %s' % invitations
            assert isinstance(applications, List), 'applications error: %s' % applications
            applications = applications.copy()
            # merge applications
            for item in invitations:
                applications.append(item)
    # 2. update applications
    if applications is not None:
        msg['applications'] = applications
    # 3. save reset command message
    return database.save_reset_command_message(group=group, content=cmd, msg=msg)
