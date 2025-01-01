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
    Messenger for client
    ~~~~~~~~~~~~~~~~~~~~

    Transform and send message
"""

from typing import Optional, List

from dimsdk import EntityType, ID, EVERYONE
from dimsdk import Document, Visa
from dimsdk import Station
from dimsdk import Envelope, InstantMessage, ReliableMessage
from dimsdk import ContentType, Command
from dimsdk import ReceiptCommand
from dimsdk import MessageUtils

from ..common import HandshakeCommand, ReportCommand, LoginCommand
from ..common import CommonMessenger

from .network import ClientSession


class ClientMessenger(CommonMessenger):

    @property
    def session(self) -> ClientSession:
        sess = super().session
        assert isinstance(sess, ClientSession), 'session error: %s' % sess
        return sess

    # Override
    async def process_reliable_message(self, msg: ReliableMessage) -> List[ReliableMessage]:
        # call super
        responses = await super().process_reliable_message(msg=msg)
        if len(responses) == 0 and self._needs_receipt(msg=msg):
            r_msg = await self._build_receipt(envelope=msg.envelope)
            if r_msg is not None:
                responses = [r_msg]
        return responses

    async def _build_receipt(self, envelope: Envelope) -> Optional[ReliableMessage]:
        current_user = await self.facebook.current_user
        text = 'Message received.'
        res = ReceiptCommand.create(text=text, envelope=envelope)
        env = Envelope.create(sender=current_user.identifier, receiver=envelope.sender)
        i_msg = InstantMessage.create(head=env, body=res)
        s_msg = await self.encrypt_message(msg=i_msg)
        if s_msg is None:
            # assert False, 'failed to encrypt message: %s -> %s' % (current_user, envelope.sender)
            return None
        r_msg = await self.sign_message(msg=s_msg)
        if r_msg is None:
            # assert False, 'failed to sign message: %s -> %s' % (current_user, envelope.sender)
            return None
        return r_msg

    # noinspection PyMethodMayBeStatic
    def _needs_receipt(self, msg: ReliableMessage) -> bool:
        if msg.type == ContentType.COMMAND:
            # filter for looping message (receipt for receipt)
            return False
        sender = msg.sender
        # receiver = msg.receiver
        # if sender.type == EntityType.STATION or sender.type == EntityType.BOT:
        #     if receiver.type == EntityType.STATION or receiver.type == EntityType.BOT:
        #         # message between bots
        #         return False
        if sender.type != EntityType.USER:  # and receiver.type != EntityType.USER:
            # message between bots
            return False
        # current_user = self.facebook.current_user
        # if receiver != current_user.identifier:
        #     # forward message
        #     return True
        # TODO: other condition?
        return True

    # Override
    async def send_instant_message(self, msg: InstantMessage, priority: int = 0) -> Optional[ReliableMessage]:
        if self.session.ready:
            # OK, any message can go out
            pass
        else:
            # not login yet
            content = msg.content
            if not isinstance(content, Command):
                self.warning(msg='not handshake yet, suspend message: %s => %s' % (content, msg.receiver))
                # TODO: suspend instant message
                return None
            elif isinstance(content, HandshakeCommand):
                # NOTICE: only handshake message can go out
                msg['pass'] = 'handshaking'
            else:
                self.warning(msg='not handshake yet, drop command: %s => %s' % (content, msg.receiver))
                # TODO: suspend instant message
                return None
        return await super().send_instant_message(msg=msg, priority=priority)

    # Override
    async def send_reliable_message(self, msg: ReliableMessage, priority: int = 0) -> bool:
        passport = msg.pop('pass', None)
        if self.session.ready:
            # OK, any message can go out
            pass
        elif passport == 'handshaking':
            # not login in yet, let the handshake message go out only
            pass
        else:
            self.warning(msg='not handshake yet, suspend message: %s => %s' % (msg.sender, msg.receiver))
            # TODO: suspend reliable message
            return False
        return await super().send_reliable_message(msg=msg, priority=priority)

    async def handshake(self, session_key: Optional[str]):
        """ send handshake command to current station """
        session = self.session
        station = session.station
        srv_id = station.identifier
        if session_key is None:
            # first handshake
            facebook = self.facebook
            user = await facebook.current_user
            assert user is not None, 'current user not found'
            env = Envelope.create(sender=user.identifier, receiver=srv_id)
            cmd = HandshakeCommand.start()
            # send first handshake command as broadcast message?
            cmd.group = Station.EVERY
            # update visa before first handshake
            await self._update_visa()
            meta = await user.meta
            visa = await user.visa
            # create instant message with meta & visa
            i_msg = InstantMessage.create(head=env, body=cmd)
            MessageUtils.set_meta(meta=meta, msg=i_msg)
            MessageUtils.set_visa(visa=visa, msg=i_msg)
            await self.send_instant_message(msg=i_msg, priority=-1)
        else:
            # handshake again
            cmd = HandshakeCommand.restart(session=session_key)
            await self.send_content(sender=None, receiver=srv_id, content=cmd, priority=-1)

    async def _update_visa(self) -> Optional[Visa]:
        facebook = self.facebook
        user = await facebook.current_user
        assert user is not None, 'current user not found'
        # 1. get sign key for current user
        pri_key = await facebook.private_key_for_visa_signature(identifier=user.identifier)
        assert pri_key is not None, 'private key not found: %s' % user.identifier
        # 2. get visa document for current user
        visa = await user.visa
        if visa is None:
            # FIXME: query from station or create a new one?
            return None
        else:
            # clone for modifying
            visa = Document.parse(document=visa.copy_dictionary(deep_copy=False))
            if not isinstance(visa, Visa):
                self.error(msg='visa error: %s' % visa)
                return None
        # 3. update visa document
        visa.set_property(name='sys', value={
            'os': 'Linux',
        })
        if visa.sign(private_key=pri_key) is None:
            self.error(msg='failed to sign visa: %s, private key: %s' % (visa, pri_key))
        elif await facebook.save_document(document=visa):
            self.info(msg='visa updated: %s' % visa)
            return visa
        else:
            self.error(msg='failed to save visa: %s' % visa)

    async def handshake_success(self):
        """ Callback for handshake success """
        # change the flag of current session
        self.info(msg='handshake success, change session accepted: %s => True' % self.session.accepted)
        self.session.accepted = True
        # broadcast current documents after handshake success
        await self.broadcast_documents()
        # TODO: let a service bot to do this job

    async def broadcast_documents(self, updated: bool = False):
        """ broadcast meta & visa document to all stations """
        facebook = self.facebook
        user = await facebook.current_user
        assert user is not None, 'current user not found'
        visa = await user.visa
        assert visa is not None, 'visa not found: %s' % user
        me = user.identifier
        #
        #  send to all contacts
        #
        checker = facebook.checker
        contacts = await facebook.get_contacts(identifier=me)
        for item in contacts:
            await checker.send_visa(visa=visa, receiver=item, updated=updated)
        #
        #  broadcast to everyone@everywhere
        #
        await checker.send_visa(visa=visa, receiver=EVERYONE, updated=updated)

    async def broadcast_login(self, sender: ID, user_agent: str):
        """ send login command to keep roaming """
        # get current station
        station = self.session.station
        assert sender.type != EntityType.STATION, 'station (%s) cannot login: %s' % (sender, station)
        # create login command
        command = LoginCommand(identifier=sender)
        command.agent = user_agent
        command.station = station
        # broadcast to everyone@everywhere
        await self.send_content(sender=sender, receiver=EVERYONE, content=command, priority=1)

    async def report_online(self, sender: ID = None):
        """ send report command to keep user online """
        command = ReportCommand(title=ReportCommand.ONLINE)
        await self.send_content(sender=sender, receiver=Station.ANY, content=command, priority=1)

    async def report_offline(self, sender: ID = None):
        """ Send report command to let user offline """
        command = ReportCommand(title=ReportCommand.OFFLINE)
        await self.send_content(sender=sender, receiver=Station.ANY, content=command, priority=1)
