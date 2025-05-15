# -*- coding: utf-8 -*-
#
#   DIM-SDK : Decentralized Instant Messaging Software Development Kit
#
#                                Written in 2022 by Moky <albert.moky@gmail.com>
#
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
    Common extensions for Messenger
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    Transform and send message
"""

from abc import ABC
from typing import Optional, Union, Tuple, List, Dict

from dimsdk import SymmetricKey
from dimsdk import ID
from dimsdk import Content, Envelope
from dimsdk import FileContent, Command
from dimsdk import InstantMessage, SecureMessage, ReliableMessage
from dimsdk import EntityDelegate, CipherKeyDelegate
from dimsdk import Messenger, Packer, Processor

from ..utils import Logging, Converter

from .dbi import MessageDBI

from .facebook import CommonFacebook
from .session import Transmitter, Session

from .queue import SuspendedMessageQueue

from .compat import Compatible


class CommonMessenger(Messenger, Transmitter, Logging, ABC):

    def __init__(self, session: Session, facebook: CommonFacebook, database: MessageDBI):
        super().__init__()
        self.__session = session
        self.__facebook = facebook
        self.__database = database
        self.__packer: Optional[Packer] = None
        self.__processor: Optional[Processor] = None
        self.__queue = SuspendedMessageQueue()

    @property  # Override
    def packer(self) -> Packer:
        return self.__packer

    @packer.setter
    def packer(self, delegate: Packer):
        self.__packer = delegate

    @property  # Override
    def processor(self) -> Processor:
        return self.__processor

    @processor.setter
    def processor(self, delegate: Processor):
        self.__processor = delegate

    @property
    def database(self) -> MessageDBI:
        return self.__database

    @property  # Override
    def key_cache(self) -> CipherKeyDelegate:
        return self.__database

    @property  # Override
    def barrack(self) -> EntityDelegate:
        return self.__facebook

    @property
    def facebook(self) -> CommonFacebook:
        return self.__facebook

    @property
    def session(self) -> Session:
        return self.__session

    def suspend_reliable_message(self, msg: ReliableMessage, error: Dict):
        self.__queue.suspend_reliable_message(msg=msg, error=error)

    def suspend_instant_message(self, msg: InstantMessage, error: Dict):
        self.__queue.suspend_instant_message(msg=msg, error=error)

    def resume_reliable_messages(self) -> List[ReliableMessage]:
        return self.__queue.resume_reliable_messages()

    def resume_instant_messages(self) -> List[InstantMessage]:
        return self.__queue.resume_instant_messages()

    # Override
    async def encrypt_key(self, data: bytes, receiver: ID, msg: InstantMessage) -> Optional[bytes]:
        try:
            return await super().encrypt_key(data=data, receiver=receiver, msg=msg)
        except Exception as error:
            # FIXME:
            self.error(msg='failed to encrypt key: %s' % error)

    # Override
    async def serialize_key(self, key: Union[dict, SymmetricKey], msg: InstantMessage) -> Optional[bytes]:
        # TODO: reuse message key
        #
        # 0. check message key
        reused = key.get('reused')
        digest = key.get('digest')
        if reused is None and digest is None:
            # flags not exist, serialize it directly
            return await super().serialize_key(key=key, msg=msg)
        # 1. remove before serializing key
        key.pop('reused', None)
        key.pop('digest', None)
        # 2. serialize key without flags
        data = await super().serialize_key(key=key, msg=msg)
        # 3. put them back after serialized
        if Converter.get_bool(value=reused, default=False):
            key['reused'] = reused
        if digest is not None:
            key['digest'] = digest
        # OK
        return data

    # Override
    async def serialize_content(self, content: Content, key: SymmetricKey, msg: InstantMessage) -> bytes:
        if isinstance(content, Command):
            content = Compatible.fix_command(content=content)
        elif isinstance(content, FileContent):
            content = Compatible.fix_file_content(content=content)
        return await super().serialize_content(content=content, key=key, msg=msg)

    # Override
    async def deserialize_content(self, data: bytes, key: SymmetricKey, msg: SecureMessage) -> Optional[Content]:
        content = await super().deserialize_content(data=data, key=key, msg=msg)
        if isinstance(content, Command):
            content = Compatible.fix_command(content=content)
        elif isinstance(content, FileContent):
            content = Compatible.fix_file_content(content=content)
        return content

    #
    #   Interfaces for Transmitting Message
    #

    # Override
    async def send_content(self,  content: Content, sender: Optional[ID], receiver: ID,
                           priority: int = 0) -> Tuple[InstantMessage, Optional[ReliableMessage]]:
        """ Send message content with priority """
        if sender is None:
            current = await self.facebook.current_user
            assert current is not None, 'current user not set'
            sender = current.identifier
        env = Envelope.create(sender=sender, receiver=receiver)
        i_msg = InstantMessage.create(head=env, body=content)
        r_msg = await self.send_instant_message(msg=i_msg, priority=priority)
        return i_msg, r_msg

    # private
    async def _attach_visa_time(self, sender: ID, msg: InstantMessage) -> bool:
        if isinstance(msg.content, Command):
            # no need to attach times for command
            return False
        doc = await self.facebook.get_visa(sender)
        if doc is None:
            self.error(msg='failed to get visa document for sender: %s' % sender)
            return False
        # attach sender document time
        last_doc_time = doc.time
        if last_doc_time is None:
            self.error(msg='document error: %s' % doc)
            return False
        else:
            msg.set_datetime(key='SDT', value=last_doc_time)
        return True

    # Override
    async def send_instant_message(self, msg: InstantMessage, priority: int = 0) -> Optional[ReliableMessage]:
        """ send instant message with priority """
        sender = msg.sender
        # 0. check cycled message
        if sender == msg.receiver:
            self.warning(msg='cycled message: %s => %s, %s' % (sender, msg.receiver, msg.group))
            # return None
        else:
            self.debug(msg='send instant message message (type=%d): %s => %s, %s'
                           % (msg.content.type, sender, msg.receiver, msg.group))
            # attach sender's document times
            # for the receiver to check whether user info synchronized
            ok = await self._attach_visa_time(sender=sender, msg=msg)
            if ok or isinstance(msg.content, Command):
                pass
            else:
                self.warning(msg='failed to attach document time: %s => %s' % (sender, msg.content))
        #
        #  1. encrypt message
        #
        s_msg = await self.encrypt_message(msg=msg)
        if s_msg is None:
            # public key not found?
            self.warning(msg='failed to encrypt message: %s => %s, %s' % (sender, msg.receiver, msg.group))
            return None
        #
        #  2. sign message
        #
        r_msg = await self.sign_message(msg=s_msg)
        if r_msg is None:
            # TODO: set msg.state = error
            raise AssertionError('failed to sign message: %s' % s_msg)
        #
        #  3. send message
        #
        if await self.send_reliable_message(msg=r_msg, priority=priority):
            return r_msg
        # failed
        self.error(msg='failed to send message: %s => %s, %s' % (sender, msg.receiver, msg.group))

    # Override
    async def send_reliable_message(self, msg: ReliableMessage, priority: int = 0) -> bool:
        """ send reliable message with priority """
        # 0. check cycled message
        if msg.sender == msg.receiver:
            self.warning(msg='cycled message: %s => %s, %s' % (msg.sender, msg.receiver, msg.group))
            # return False
        # 1. serialize message
        data = await self.serialize_message(msg=msg)
        assert data is not None, 'failed to serialize message: %s' % msg
        # 2. call gate keeper to send the message data package
        #    put message package into the waiting queue of current session
        session = self.session
        return await session.queue_message_package(msg=msg, data=data, priority=priority)
