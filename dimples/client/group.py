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

from typing import Optional, List, Dict

from dimsdk import EntityType, ID, ANYONE, FOUNDER
from dimsdk import Document, Meta
from dimsdk import User, GroupDataSource
from dimsdk import Content, Command, MetaCommand, DocumentCommand, GroupCommand

from ..utils import Singleton
from ..common import CommonFacebook, CommonMessenger


@Singleton
class GroupManager(GroupDataSource):
    """ This is for sending group message, or managing group members """

    def __init__(self):
        super().__init__()
        self.__messenger = None  # ClientMessenger
        self._cache_group_founders:   Dict[ID, ID] = {}
        self._cache_group_owners:     Dict[ID, ID] = {}
        self._cache_group_members:    Dict[ID, List[ID]] = {}
        self._cache_group_assistants: Dict[ID, List[ID]] = {}
        self._default_assistants:     List[ID] = []

    @property
    def facebook(self) -> Optional[CommonFacebook]:
        messenger = self.messenger
        assert messenger is not None, 'messenger not set yet'
        return messenger.facebook

    @property
    def messenger(self) -> Optional[CommonMessenger]:
        return self.__messenger

    @messenger.setter
    def messenger(self, transceiver: CommonMessenger):
        self.__messenger = transceiver

    @property
    def current_user(self) -> Optional[User]:
        facebook = self.facebook
        assert facebook is not None, 'facebook not found'
        return facebook.current_user

    def send_content(self, content: Content, group: ID) -> bool:
        """ Send group message content """
        gid = content.group
        if gid is None:
            content.group = group
        elif gid != group:
            raise AssertionError('group ID not match: %s, %s' % (gid, group))
        messenger = self.messenger
        assert messenger is not None, 'messenger not set yet'
        assistants = self.assistants(identifier=group)
        for bot in assistants:
            # send to any bot
            result = messenger.send_content(sender=None, receiver=bot, content=content)
            if result[1] is not None:
                # only send to one bot, let the bot to split and
                # forward this message to all members
                return True

    # private
    def send_command(self, content: Command, receiver: ID = None, members: List[ID] = None):
        messenger = self.messenger
        assert messenger is not None, 'messenger not set yet'
        if receiver is not None:
            messenger.send_content(sender=None, receiver=receiver, content=content)
        if members is not None:
            sender = self.current_user
            sender = None if sender is None else sender.identifier
            for item in members:
                messenger.send_content(sender=sender, receiver=item, content=content)

    def invite(self, group: ID, member: ID = None, members: List[ID] = None) -> bool:
        """ Invite new members to this group
            (only existed member/assistant can do this)
        """
        if members is None:
            assert member is not None, 'group member empty'
            new_members = [member]
        else:
            new_members = members
        # TODO: make sure group meta exists
        # TODO: make sure current user is a member

        # 0. build 'meta/document' command
        meta = self.meta(identifier=group)
        if meta is None:
            raise AssertionError('failed to get meta for group: %s' % group)
        visa = self.document(identifier=group, doc_type='*')
        if visa is None:
            # empty document
            command = MetaCommand.response(identifier=group, meta=meta)
        else:
            command = DocumentCommand.response(identifier=group, meta=meta, document=visa)
        bots = self.assistants(identifier=group)
        # 1. send 'meta/document' command
        self.send_command(content=command, members=bots)                # to all assistants
        # 2. update local members and notice all bots & members
        members = self.members(identifier=group)
        if len(members) <= 2:  # new group?
            # 2.0. update local storage
            members = self.add_members(members=new_members, group=group)
            # 2.1. send 'meta/document' command
            self.send_command(content=command, members=members)         # to all members
            # 2.2. send 'invite' command with all members
            command = GroupCommand.invite(group=group, members=members)
            self.send_command(content=command, members=bots)            # to group assistants
            self.send_command(content=command, members=members)         # to all members
        else:
            # 2.1. send 'meta/document' command
            # self.send_command(content=command, members=members)       # to old members
            self.send_command(content=command, members=new_members)     # to new members
            # 2.2. send 'invite' command with new members only
            command = GroupCommand.invite(group=group, members=new_members)
            self.send_command(content=command, members=bots)            # to group assistants
            self.send_command(content=command, members=members)         # to old members
            # 2.3. update local storage
            members = self.add_members(members=new_members, group=group)
            # 2.4. send 'invite' command with all members
            command = GroupCommand.invite(group=group, members=members)
            self.send_command(content=command, members=new_members)     # to new members
        return True

    def expel(self, group: ID, member: ID = None, members: List[ID] = None) -> bool:
        """ Expel members from this group
            (only group owner/assistant can do this)
        """
        if members is None:
            assert member is not None, 'group member empty'
            out_members = [member]
        else:
            out_members = members
        owner = self.owner(identifier=group)
        bots = self.assistants(identifier=group)
        # TODO: make sure group meta exists
        # TODO: make sure current user is the owner

        # 0. check permission
        for item in bots:
            if item in out_members:
                raise AssertionError('cannot expel group assistant: %s, group: %s' % (item, group))
        if owner in out_members:
            raise AssertionError('cannot expel group owner: %s, group: %s' % (owner, group))
        # 1. update local storage
        members = self.remove_members(members=out_members, group=group)
        # 2. send 'expel' command
        command = GroupCommand.expel(group=group, members=out_members)
        self.send_command(content=command, members=bots)                # to group assistants
        self.send_command(content=command, members=members)             # to new members
        self.send_command(content=command, members=out_members)         # to expelled members
        return True

    def quit(self, group: ID) -> bool:
        """ Quit from this group
            (only group member can do this)
        """
        user = self.current_user
        if user is None:
            raise AssertionError('failed to get current user')
        me = user.identifier
        bots = self.assistants(identifier=group)
        owner = self.owner(identifier=group)
        members = self.members(identifier=group)
        # 0. check permission
        if me in bots:
            raise AssertionError('group assistant cannot quit: %s, group: %s' % (me, group))
        elif me == owner:
            raise AssertionError('group owner cannot quit: %s, group: %s' % (me, group))
        # 1. update local storage
        if me in members:
            members.remove(me)
            ok = self.save_members(members=members, group=group)
        else:
            # not a member now
            ok = False
        # 2. send 'quit' command
        command = GroupCommand.quit(group=group)
        self.send_command(content=command, members=bots)                # to group assistants
        self.send_command(content=command, members=members)             # to new members
        return ok

    def query(self, group: ID) -> bool:
        """ Query group info """
        messenger = self.messenger
        assert messenger is not None, 'messenger not set yet'
        return messenger.query_members(identifier=group)

    #
    #   EntityDataSource
    #

    # Override
    def meta(self, identifier: ID) -> Optional[Meta]:
        facebook = self.facebook
        assert facebook is not None, 'facebook not found'
        return facebook.meta(identifier=identifier)

    # Override
    def document(self, identifier: ID, doc_type: str = '*') -> Optional[Document]:
        facebook = self.facebook
        assert facebook is not None, 'facebook not found'
        return facebook.document(identifier=identifier, doc_type=doc_type)

    #
    #   GroupDataSource
    #

    # Override
    def founder(self, identifier: ID) -> Optional[ID]:
        user = self._cache_group_founders.get(identifier)
        if user is None:
            facebook = self.facebook
            assert facebook is not None, 'facebook not found'
            user = facebook.founder(identifier=identifier)
            if user is None:
                user = FOUNDER  # place holder
            self._cache_group_founders[identifier] = user
        return None if user.is_broadcast else user

    # Override
    def owner(self, identifier: ID) -> Optional[ID]:
        user = self._cache_group_owners.get(identifier)
        if user is None:
            facebook = self.facebook
            assert facebook is not None, 'facebook not found'
            user = facebook.owner(identifier=identifier)
            if user is None:
                user = ANYONE  # place holder
            self._cache_group_owners[identifier] = user
        return None if user.is_broadcast else user

    # Override
    def members(self, identifier: ID) -> List[ID]:
        users = self._cache_group_members.get(identifier)
        if users is None:
            facebook = self.facebook
            assert facebook is not None, 'facebook not found'
            users = facebook.members(identifier=identifier)
            if users is None:
                users = []  # place holder
            self._cache_group_members[identifier] = users
        return users

    # Override
    def assistants(self, identifier: ID) -> List[ID]:
        users = self._cache_group_assistants.get(identifier)
        if users is None:
            facebook = self.facebook
            assert facebook is not None, 'facebook not found'
            users = facebook.assistants(identifier=identifier)
            if users is None:
                users = []  # place holder
            self._cache_group_assistants[identifier] = users
        if len(users) == 0:
            # get from global setting
            users = self._default_assistants
            if len(users) == 0:
                # TODO: get from ANS
                pass
        return users

    #
    #   MemberShip
    #

    def is_founder(self, member: ID, group: ID) -> bool:
        founder = self.founder(identifier=group)
        if founder is not None:
            return founder == member
        # check member's public key with group's meta.key
        g_meta = self.meta(identifier=group)
        m_meta = self.meta(identifier=member)
        if g_meta is None or m_meta is None:
            assert False, 'failed to get meta: %s, %s' % (member, group)
        return Meta.match_key(meta=g_meta, key=m_meta.key)

    def is_owner(self, member: ID, group: ID) -> bool:
        owner = self.owner(identifier=group)
        if owner is not None:
            return owner == member
        if group.type == EntityType.GROUP:
            # this is a polylogue
            return self.is_founder(member=member, group=group)
        assert False, 'only Polylogue so far: %s' % group

    #
    #   Members
    #

    def contains_member(self, member: ID, group: ID) -> bool:
        all_members = self.members(identifier=group)
        if member in all_members:
            return True
        owner = self.owner(identifier=group)
        return member == owner

    def add_member(self, member: ID, group: ID) -> bool:
        all_members = self.members(identifier=group)
        if member in all_members:
            # already exists
            return False
        all_members.append(member)
        return self.save_members(members=all_members, group=group)

    def remove_member(self, member: ID, group: ID) -> bool:
        all_members = self.members(identifier=group)
        if member not in all_members:
            # not exists
            return False
        all_members.remove(member)
        return self.save_members(members=all_members, group=group)

    def add_members(self, members: List[ID], group: ID) -> List[ID]:
        all_members = self.members(identifier=group)
        count = 0
        for item in members:
            if item in all_members:
                continue
            all_members.append(item)
            count += 1
        if count > 0:
            self.save_members(members=all_members, group=group)
        return all_members

    def remove_members(self, members: List[ID], group: ID) -> List[ID]:
        all_members = self.members(identifier=group)
        count = 0
        for item in members:
            if item not in all_members:
                continue
            all_members.remove(item)
            count += 1
        if count > 0:
            self.save_members(members=all_members, group=group)
        return all_members

    def save_members(self, members: List[ID], group: ID) -> bool:
        facebook = self.facebook
        assert facebook is not None, 'facebook not found'
        db = facebook.database
        assert db is not None, 'account database not set'
        if db.save_members(members=members, group=group):
            # erase cache for reload
            self._cache_group_members.pop(group, None)
            return True

    #
    #   Assistants
    #

    def contains_assistants(self, bot: ID, group: ID) -> bool:
        assistants = self.assistants(identifier=group)
        if assistants is self._default_assistants:
            # not found
            return False
        return bot in assistants

    def add_assistant(self, bot: ID, group: ID = None) -> bool:
        if group is None:
            assert bot not in self._default_assistants, 'duplicated: %s' % bot
            self._default_assistants.insert(0, bot)
            return True
        assistants = self.assistants(identifier=group)
        if assistants is self._default_assistants:
            # not found
            assistants = []
        elif bot in assistants:
            # already exists
            return False
        assistants.insert(0, bot)
        return self.save_assistants(bots=assistants, group=group)

    def save_assistants(self, bots: List[ID], group: ID) -> bool:
        facebook = self.facebook
        assert facebook is not None, 'facebook not found'
        db = facebook.database
        assert db is not None, 'account database not set'
        if db.save_assistants(assistants=bots, group=group):
            # erase cache for reload
            self._cache_group_assistants.pop(group, None)
            return True

    def remove_group(self, group: ID) -> bool:
        # TODO: remove group completely
        pass
