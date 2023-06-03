# -*- coding: utf-8 -*-
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
    Document Command Processor
    ~~~~~~~~~~~~~~~~~~~~~~~~~~

"""

from typing import Optional, List

from dimp import EntityType, ID
from dimp import ReliableMessage
from dimp import Content, ForwardContent, DocumentCommand

from dimsdk.cpu import DocumentCommandProcessor as SuperCommandProcessor

from ...common import CommonFacebook, CommonMessenger
from ...common import Session, SessionDBI


class DocumentCommandProcessor(SuperCommandProcessor):

    @property
    def facebook(self) -> CommonFacebook:
        barrack = super().facebook
        assert isinstance(barrack, CommonFacebook), 'facebook error: %s' % barrack
        return barrack

    @property
    def session(self) -> Session:
        messenger = self.messenger
        assert isinstance(messenger, CommonMessenger), 'messenger error: %s' % messenger
        return messenger.session

    # Override
    def process(self, content: Content, msg: ReliableMessage) -> List[Content]:
        assert isinstance(content, DocumentCommand), 'document command error: %s' % content
        responses = super().process(content=content, msg=msg)
        if content.document is None:
            # this is a request, check DocumentCommand & LoginCommand
            if has_document(contents=responses):
                db = self.session.database
                current = self.facebook.current_user
                sid = current.identifier
                assert db is not None, 'session DB not found'
                assert sid is not None, 'current station not found: %s' % current
                # forward login message after document command
                res = forward_login_msg(doc_id=content.identifier, sender=msg.sender, node=sid, database=db)
                if res is not None:
                    responses.append(res)
        return responses


def has_document(contents: List[Content]) -> bool:
    for item in contents:
        if isinstance(item, DocumentCommand):
            return True


def forward_login_msg(doc_id: ID, sender: ID, node: ID, database: SessionDBI) -> Optional[ForwardContent]:
    login_msg = get_login_msg(doc_id=doc_id, sender=sender, node=node, database=database)
    if login_msg is not None:
        # respond login command
        return ForwardContent.create(message=login_msg)


def get_login_msg(doc_id: ID, sender: ID, node: ID, database: SessionDBI) -> Optional[ReliableMessage]:
    """
    Get login message for document command

    :param doc_id:   document command ID
    :param sender:   sender ID
    :param node:     current node ID
    :param database: session database
    :return: login message (reliable and broadcast)
    """
    if sender == node:
        # the station is querying itself, ignore it
        return None
    elif sender.type == EntityType.BOT:
        # no need to respond LoginCommand message to a bot,
        # just ignore it
        return None
    cmd, msg = database.login_command_message(user=doc_id)
    if cmd is not None:
        if sender.type == EntityType.STATION:
            # this is a request from another station.
            # if the user is not roaming to this station, just ignore it,
            # let the target station to respond.
            roaming = cmd.station
            assert isinstance(roaming, dict), 'login command error: %s' % cmd
            sid = ID.parse(identifier=roaming.get('ID'))
            if sid != node:
                # not my guest, ignore it.
                return None
        return msg
