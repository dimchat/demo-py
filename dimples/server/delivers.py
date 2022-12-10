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

"""
    Special Delivers
    ~~~~~~~~~~~~~~~~

    Delegates for broadcast or grouped message
"""

from typing import Optional, Set, List

from dimsdk import ID, EVERYONE
from dimsdk import ReliableMessage
from dimsdk import Content
from dimsdk import Station

from ..utils import Logging
from ..common import ReceiptCommand
from ..common import SessionDBI
from ..common import CommonFacebook
from ..conn.session import get_sig

from .session_center import SessionCenter
from .dispatcher import Deliver
from .dispatcher import Dispatcher


class BroadcastDeliver(Deliver, Logging):
    """ Special deliver for broadcast message """

    def __init__(self, database: SessionDBI):
        super().__init__()
        self.__database = database

    @property
    def database(self) -> Optional[SessionDBI]:
        return self.__database

    def __get_recipients(self, msg: ReliableMessage, receiver: ID) -> Set[ID]:
        recipients = set()
        if receiver in ['archivist@anywhere', 'archivists@everywhere']:
            # get bot for search command
            self.debug(msg='forward to archivist: %s' % receiver)
            # get from ANS
            bot = ID.parse(identifier='archivist')
            if bot is not None:
                recipients.add(bot)
        elif receiver in [Station.EVERY, EVERYONE]:
            # if this message sent to 'stations@everywhere' or 'everyone@everywhere'
            # get all neighbor stations to broadcast, but
            # traced nodes should be ignored to avoid cycled delivering
            self.debug(msg='forward to neighbors: %s' % receiver)
            traces = msg.get('traces')
            if traces is None:
                traces = []
            db = self.database
            neighbors = db.all_neighbors()
            for item in neighbors:
                sid = item[2]
                if sid is None or sid in traces:
                    self.warning(msg='ignore node: %s' % str(item))
                    continue
                recipients.add(sid)
            self.debug(msg='recipients: %s => %s' % (receiver, recipients))
        else:
            self.warning(msg='unknown broadcast ID: %s' % receiver)
        return recipients

        # TODO: after deliver to connected neighbors, the dispatcher will continue
        #       delivering via station bridge, should we mark 'sent_neighbors' in
        #       only one message to the bridge, let the bridge to separate for other
        #       neighbors which not connect to this station directly?

    # Override
    def deliver_message(self, msg: ReliableMessage, receiver: ID) -> List[Content]:
        assert receiver.is_broadcast, 'broadcast ID error: %s' % receiver
        sender = msg.sender
        # get all actual recipients
        recipients = self.__get_recipients(msg=msg, receiver=receiver)
        if recipients is None or len(recipients) == 0:
            # # error
            # text = 'Broadcast not deliver'
            # cmd = ReceiptCommand.create(text=text, msg=msg)
            # return [cmd]
            return []
        # deliver to all recipients one by one
        self.info(msg='delivering message (%s) from %s to %s, actual receivers: %s'
                      % (get_sig(msg=msg), sender, receiver, ID.revert(recipients)))
        dispatcher = Dispatcher()
        for target in recipients:
            assert not target.is_broadcast, 'target ID error: %s, %s => %s'\
                                            % (target, receiver, ID.revert(members=recipients))
            dispatcher.deliver_message(msg=msg, receiver=target)
        # responses
        text = 'Broadcast message delivering'
        cmd = ReceiptCommand.create(text=text, msg=msg)
        cmd['recipients'] = ID.revert(members=recipients)
        return [cmd]


class GroupDeliver(Deliver, Logging):
    """ Special deliver for grouped message """

    def __init__(self, facebook: CommonFacebook):
        super().__init__()
        self.__facebook = facebook

    @property
    def facebook(self) -> Optional[CommonFacebook]:
        return self.__facebook

    def __get_assistant(self, group: ID) -> Optional[ID]:
        facebook = self.facebook
        assistants = facebook.assistants(identifier=group)
        if assistants is None or len(assistants) == 0:
            # group assistant not found
            # get from ANS?
            return ID.parse(identifier='assistant')
        center = SessionCenter()
        for bot in assistants:
            if center.is_active(identifier=bot):
                # first online bot
                return bot
        # first bot
        return assistants[0]

    # Override
    def deliver_message(self, msg: ReliableMessage, receiver: ID) -> List[Content]:
        assert receiver.is_group, 'group ID error: %s' % receiver
        sender = msg.sender
        # get first assistant
        bot = self.__get_assistant(group=receiver)
        if bot is None:
            # error
            self.error(msg='group assistant not found: %s' % receiver)
            text = 'Group assistant not found'
            cmd = ReceiptCommand.create(text=text, msg=msg)
            return [cmd]
        else:
            # replace group ID
            group = msg.group
            if group is None:
                msg['group'] = str(receiver)
                msg['receiver'] = str(bot)
            else:
                assert group == receiver, 'group ID not matched: %s => %s' % (group, receiver)
                self.warning(msg='group ID exists: %s' % group)
        self.info(msg='delivering message (%s) from %s to %s, bot: %s'
                      % (get_sig(msg=msg), sender, receiver, bot))
        # deliver to all recipients one by one
        dispatcher = Dispatcher()
        dispatcher.deliver_message(msg=msg, receiver=bot)
        # responses
        text = 'Group message delivering'
        cmd = ReceiptCommand.create(text=text, msg=msg)
        cmd['recipients'] = [str(bot)]
        return [cmd]
