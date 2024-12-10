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

from typing import Optional, List

from dimsdk import ID
from dimsdk import Content, ForwardContent
from dimsdk import MetaCommand, DocumentCommand
from dimsdk import GroupCommand
from dimsdk import Station

from ..utils import Logging
from ..common import AccountDBI
from ..common import CommonFacebook, CommonMessenger
from ..common import Register

from .delegate import GroupDelegate
from .packer import GroupPacker
from .helper import GroupCommandHelper
from .builder import GroupHistoryBuilder


class GroupManager(Logging):

    def __init__(self, delegate: GroupDelegate):
        super().__init__()
        self.__delegate = delegate
        self.__packer = self._create_packer()
        self.__helper = self._create_helper()
        self.__builder = self._create_builder()

    def _create_packer(self) -> GroupPacker:
        """ override for customized packer """
        return GroupPacker(self.__delegate)

    def _create_helper(self) -> GroupCommandHelper:
        """ override for customized helper """
        return GroupCommandHelper(self.__delegate)

    def _create_builder(self) -> GroupHistoryBuilder:
        """ override for customized builder """
        return GroupHistoryBuilder(self.__delegate)

    @property  # protected
    def delegate(self) -> GroupDelegate:
        return self.__delegate

    @property  # protected
    def packer(self) -> GroupPacker:
        return self.__packer

    @property  # protected
    def helper(self) -> GroupCommandHelper:
        return self.__helper

    @property  # protected
    def builder(self) -> GroupHistoryBuilder:
        return self.__builder

    @property  # protected
    def facebook(self) -> CommonFacebook:
        return self.__delegate.facebook

    @property  # protected
    def messenger(self) -> CommonMessenger:
        return self.__delegate.messenger

    @property  # protected
    def database(self) -> AccountDBI:
        return self.__delegate.facebook.archivist.database

    async def create_group(self, members: List[ID]) -> Optional[ID]:
        """
        Create new group with members
        (broadcast document & members to all members and neighbor station)

        :param members: initial group members
        :return: new group ID
        """
        assert len(members) > 1, 'not enough members: %s' % str(members)
        #
        #   0. get current user
        #
        user = await self.facebook.current_user
        if user is None:
            self.error(msg='failed to get current user')
            return None
        founder = user.identifier
        #
        #   1. check founder (owner)
        #
        pos = find(founder, array=members)
        if pos < 0:
            # put me in the first position
            members.insert(0, founder)
        elif pos > 0:
            # move me to the front
            members.pop(pos)
            members.insert(0, founder)
        # generate group name
        title = await self.delegate.build_group_name(members=members)
        #
        #   2. create group with name
        #
        register = Register(database=self.database)
        group = await register.create_group(founder=founder, name=title)
        self.info(msg='new group: %s (%s), founder: %s' % (group, title, founder))
        #
        #   3. upload meta+document to neighbor station(s)
        #   DISCUSS: should we let the neighbor stations know the group info?
        #
        meta = await self.delegate.get_meta(identifier=group)
        doc = await self.delegate.get_bulletin(group)
        if doc is not None:
            content = DocumentCommand.response(identifier=group, meta=meta, document=doc)
        elif meta is not None:
            content = MetaCommand.response(identifier=group, meta=meta)
        else:
            self.error(msg='failed to get group info: %s' % group)
            return None
        await self.__send_command(content=content, receiver=Station.ANY)      # to neighbor(s)
        #
        #   4. create & broadcast 'reset' group command with new members
        #
        if await self.reset_members(members=members, group=group):
            self.info(msg='created group with %d members: %s' % (len(members), group))
        else:
            self.error(msg='failed to create group with %d members: %s' % (len(members), group))
        return group

    """
        DISCUSS: should we let the neighbor stations know the group info?
        
            (A) if we do this, it can provide a convenience that,
                when someone receive a message from an unknown group,
                it can query the group info from the neighbor immediately;
                and its potential risk is that anyone not in the group can also
                know the group info (only the group ID, name, and admins, ...)
                
            (B) but, if we don't let the station knows it,
                then we must shared the group info with our members themselves;
                and if none of them is online, you cannot get the newest info
                immediately until someone online again.
    """

    async def reset_members(self, members: List[ID], group: ID) -> bool:
        """
        Reset group members
        (broadcast new group history to all members)

        :param members: new member list
        :param group:   group ID
        :return: False on error
        """
        assert group.is_group and len(members) > 0, 'params error: %s, %s' % (group, members)
        #
        #   0. get current user
        #
        user = await self.facebook.current_user
        if user is None:
            self.error(msg='failed to get current user')
            return False
        me = user.identifier
        # check member list
        first = members[0]
        ok = await self.delegate.is_owner(user=first, group=group)
        if not ok:
            self.error(msg='group owner must be the first member: %s' % group)
            return False
        # member list OK, check expelled members
        old_members = await self.delegate.get_members(identifier=group)
        expel_list = []
        for item in old_members:
            if item not in members:
                expel_list.append(item)
        #
        #   1. check permission
        #
        is_owner = me == first
        is_admin = await self.delegate.is_administrator(user=me, group=group)
        is_bot = await self.delegate.is_assistant(user=me, group=group)
        can_reset = is_owner or is_admin
        if not can_reset:
            self.error(msg='cannot reset members of group: %s' % group)
            return False
        # only the owner or admin can reset group member
        assert not is_bot, 'group bot cannot reset members: %s, %s' % (group, me)
        #
        #   2. build 'reset' command
        #
        reset, msg = await self.builder.builder_reset_command(group=group, members=members)
        if reset is None or msg is None:
            self.error(msg='failed to build "reset" command for group: %s' % group)
            return False
        #
        #   3. save 'reset' command, and update new members
        #
        if not await self.helper.save_group_history(group=group, content=reset, message=msg):
            self.error(msg='failed to save "reset" command for group: %s' % group)
            return False
        elif not await self.delegate.save_members(members=members, group=group):
            self.error(msg='failed to update members of group: %s' % group)
            return False
        else:
            self.info(msg='group members updated: %s, %d' % (group, len(members)))
        #
        #   4. forward all group history
        #
        messages = await self.builder.build_group_histories(group=group)
        forward = ForwardContent.create(messages=messages)
        bots = await self.delegate.get_assistants(identifier=group)
        if len(bots) > 0:
            # let the group bots know the newest member ID list,
            # so they can split group message correctly for us.
            return await self.__send_command(content=forward, members=bots)   # to all assistants
        else:
            # group bots not exist,
            # send the command to all members
            await self.__send_command(content=forward, members=members)       # to new members
            await self.__send_command(content=forward, members=expel_list)    # to removed members
        return True

    async def invite_members(self, members: List[ID], group: ID) -> bool:
        """
        Invite new members to this group


        :param members: inviting member list
        :param group:   group ID
        :return: False on error
        """
        assert group.is_group and len(members) > 0, 'params error: %s, %s' % (group, members)
        #
        #   0. get current user
        #
        user = await self.facebook.current_user
        if user is None:
            self.error(msg='failed to get current user')
            return False
        me = user.identifier

        old_members = await self.delegate.get_members(identifier=group)
        is_owner = await self.delegate.is_owner(user=me, group=group)
        is_admin = await self.delegate.is_administrator(user=me, group=group)
        is_member = await self.delegate.is_member(user=me, group=group)
        #
        #   1. check permission
        #
        can_reset = is_owner or is_admin
        if can_reset:
            all_members = old_members.copy()
            for item in members:
                if item not in all_members:
                    all_members.append(item)
            return await self.reset_members(members=all_members, group=group)
        elif not is_member:
            self.error(msg='cannot invite member into group: %s' % group)
            return False
        # invited by ordinary member

        #
        #   2. build 'invite' command
        #
        invite = GroupCommand.invite(group=group, members=members)
        r_msg = await self.packer.pack_message(content=invite, sender=me)
        if r_msg is None:
            self.error(msg='failed to build "invite" command for group: %s' % group)
            return False
        elif not await self.helper.save_group_history(group=group, content=invite, message=r_msg):
            self.error(msg='failed to save "invite" command for group: %s' % group)
            return False
        forward = ForwardContent.create(message=r_msg)
        #
        #   3. forward group command(s)
        #
        bots = await self.delegate.get_assistants(identifier=group)
        if len(bots) > 0:
            # let the group bots know the newest member ID list,
            # so they can split group message correctly for us.
            return await self.__send_command(content=forward, members=bots)   # to all assistants
        # forward 'invite' to old members
        await self.__send_command(content=forward, members=old_members)       # to old members
        # forward all group history to new members
        messages = await self.builder.build_group_histories(group=group)
        forward = ForwardContent.create(messages=messages)
        # TODO: remove that members already exist before sending?
        await self.__send_command(content=forward, members=members)           # to new members
        return True

    async def quit_group(self, group: ID) -> bool:
        """
        Quit from this group
        (broadcast a 'quit' command to all members)

        :param group: group ID
        :return: False on error
        """
        assert group.is_group, 'group ID error: %s' % group
        #
        #   0. get current user
        #
        user = await self.facebook.current_user
        if user is None:
            self.error(msg='failed to get current user')
            return False
        me = user.identifier

        members = await self.delegate.get_members(identifier=group)
        assert len(members) > 0, 'failed to get members for group: %s' % group
        is_owner = await self.delegate.is_owner(user=me, group=group)
        is_admin = await self.delegate.is_administrator(user=me, group=group)
        is_bot = await self.delegate.is_assistant(user=me, group=group)
        is_member = me in members
        #
        #   1. check permission
        #
        if is_owner:
            self.warning(msg='owner cannot quit from group: %s' % group)
            return False
        elif is_admin:
            self.warning(msg='administrator cannot quit from group: %s' % group)
            return False
        assert not is_bot, 'group bot cannot quit: %s, %s' % (group, me)
        #
        #   2. update local storage
        #
        if is_member:
            self.warning(msg='quitting group: %s, %s' % (group, me))
            new_members = members.copy()
            new_members.remove(me)
            ok = await self.delegate.save_members(members=new_members, group=group)
            assert ok, 'failed to save members for group: %s' % group
            members = new_members
        else:
            self.warning(msg='members not in group: %s, %s' % (group, me))
        #
        #   3. build 'quit' command
        #
        content = GroupCommand.quit(group=group)
        r_msg = await self.packer.pack_message(content=content, sender=me)
        if r_msg is None:
            self.error(msg='failed to pack group message: %s' % group)
            return False
        forward = ForwardContent.create(message=r_msg)
        #
        #   4. forward 'quit' command
        #
        bots = await self.delegate.get_assistants(identifier=group)
        if len(bots) > 0:
            # let the group bots know the newest member ID list,
            # so they can split group message correctly for us.
            return await self.__send_command(content=forward, members=bots)   # to group bots
        # group bots not exist,
        # send the command to all members directly
        return await self.__send_command(content=forward, members=members)    # to all members

    async def __send_command(self, content: Content, receiver: ID = None, members: List[ID] = None) -> bool:
        if receiver is not None:
            assert members is None, 'params error: %s, %s' % (receiver, members)
            members = [receiver]
        elif members is None:
            # assert False, 'params error'
            return False
        # 1. get sender
        user = await self.facebook.current_user
        if user is None:
            self.error(msg='failed to get current user')
            return False
        me = user.identifier
        # 2. send to all receivers
        messenger = self.messenger
        for receiver in members:
            if me == receiver:
                self.info(msg='skip cycled message: %s => %s' % (me, receiver))
                continue
            await messenger.send_content(sender=me, receiver=receiver, content=content, priority=1)
        return True


def find(item, array: List) -> int:
    pos = 0
    for e in array:
        if e == item:
            return pos
        else:
            pos += 1
    # not found
    return -1
