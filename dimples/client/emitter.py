# -*- coding: utf-8 -*-
#
#   DIM-SDK : Decentralized Instant Messaging Software Development Kit
#
#                                Written in 2024 by Moky <albert.moky@gmail.com>
#
# ==============================================================================
# MIT License
#
# Copyright (c) 2024 Albert Moky
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

from abc import ABC, abstractmethod
from typing import Optional, Tuple, Dict

from dimsdk import URI
from dimsdk import PortableNetworkFile, TransportableData
from dimsdk import SymmetricKey
from dimsdk import ID, User
from dimsdk import Envelope, Content, TextContent, FileContent
from dimsdk import InstantMessage, ReliableMessage

from ..utils import Logging
from ..common import Password
from ..common import Transmitter
from ..group import SharedGroupManager


class Emitter(Logging, ABC):

    @property
    @abstractmethod
    async def current_user(self) -> Optional[User]:
        raise NotImplemented

    @property
    @abstractmethod
    def messenger(self) -> Optional[Transmitter]:
        raise NotImplemented

    async def send_text(self, text: str, receiver: ID,
                        extra: Dict = None) -> Tuple[Optional[InstantMessage], Optional[ReliableMessage]]:
        """
        Send text message to receiver

        :param text:     text message
        :param extra:
        :param receiver: receiver ID
        :return: packed message
        """
        assert len(text) > 0, 'text message should not empty'
        # create text content
        content = TextContent.create(text=text)
        if self.check_markdown(text=text):
            self.info(msg='send text as markdown: "%s" => %s' % (text, receiver))
            content['format'] = 'markdown'
        else:
            self.info(msg='send text as plain: "%s" -> %s' % (text, receiver))
        # set extra params
        if extra is not None:
            for key in extra:
                content[key] = extra[key]
        return await self.send_content(content=content, sender=None, receiver=receiver)

    # noinspection PyMethodMayBeStatic
    def check_markdown(self, text: str) -> bool:
        if text.find('://') > 0:
            return True
        elif text.find('\n> ') > 0:
            return True
        elif text.find('\n# ') > 0:
            return True
        elif text.find('\n## ') > 0:
            return True
        elif text.find('\n### ') > 0:
            return True
        pos = text.find('```')
        if pos >= 0:
            pos += 3
            nxt = text[pos:pos+1]
            if nxt != '`':
                return text.find('```', pos + 1) > 0

    async def send_voice(self, mp4: bytes, receiver: ID, filename: str, duration: float, extra: Dict = None) -> bool:
        """
        Send voice message to receiver

        :param mp4:      voice data
        :param filename: '$encoded.mp4'
        :param duration: length
        :param extra:
        :param receiver: receiver ID
        :return:
        """
        assert len(mp4) > 0, 'voice data should not empty'
        ted = TransportableData.create(data=mp4)
        # create audio content
        content = FileContent.audio(data=ted, filename=filename)
        # set voice data length & duration
        content['length'] = len(mp4)
        content['duration'] = duration
        # set extra params
        if extra is not None:
            for key in extra:
                content[key] = extra[key]
        return await self.send_file_content(content=content, sender=None, receiver=receiver)

    async def send_picture(self, jpeg: bytes, receiver: ID, filename: str,
                           thumbnail: Optional[PortableNetworkFile], extra: Dict = None) -> bool:
        """
        Send picture to receiver

        :param jpeg:      image data
        :param filename:  '$encoded.jpeg'
        :param thumbnail: image thumbnail
        :param extra:
        :param receiver:  receiver ID
        :return:
        """
        assert len(jpeg) > 0, 'image data should not empty'
        ted = TransportableData.create(data=jpeg)
        # create image content
        content = FileContent.image(data=ted, filename=filename)
        # set image data length
        content['length'] = len(jpeg)
        # set extra params
        if thumbnail is not None:
            content.thumbnail = thumbnail
        if extra is not None:
            for key in extra:
                content[key] = extra[key]
        return await self.send_file_content(content=content, sender=None, receiver=receiver)

    async def send_movie(self, receiver: ID, url: URI,
                         snapshot: Optional[PortableNetworkFile], title: Optional[str],
                         filename: str = None, extra: Dict = None) -> bool:
        """
        Send movie to receiver

        :param url:      video URL
        :param snapshot: cover URL
        :param title:    video title
        :param filename:
        :param extra:
        :param receiver: receiver ID
        :return:
        """
        # create video content
        content = FileContent.video(filename=filename, url=url, password=Password.kPlainKey)
        # set extra params
        if snapshot is not None:
            content.snapshot = snapshot
        if title is not None:
            content['title'] = title
        if extra is not None:
            for key in extra:
                content[key] = extra[key]
        return await self.send_file_content(content=content, sender=None, receiver=receiver)

    async def send_content(self, content: Content, sender: Optional[ID], receiver: ID,
                           priority: int = 0) -> Tuple[Optional[InstantMessage], Optional[ReliableMessage]]:
        """ Send content """
        # check sender
        if sender is None:
            user = await self.current_user
            assert user is not None, 'failed to get current user'
            sender = user.identifier
        # check receiver
        if receiver.is_group:
            assert content.group is None or content.group == receiver, 'group ID error: %s, %s' % (receiver, content)
            content.group = receiver
        # check file content
        if isinstance(content, FileContent) and content.data is not None:
            # To avoid traffic congestion, sending a message with file data inside is not allowed,
            # you should upload the encrypted data to a CDN server first, and then
            # send the message with a download URL to the receiver.
            ok = await self.send_file_content(content=content, sender=sender, receiver=receiver, priority=priority)
            assert ok, 'failed to send file content: %s -> %s' % (sender, receiver)
            return None, None
        # pack message
        envelope = Envelope.create(sender=sender, receiver=receiver)
        i_msg = InstantMessage.create(head=envelope, body=content)
        # send message
        r_msg = await self.send_instant_message(msg=i_msg, priority=priority)
        if r_msg is not None or receiver.is_group:
            # OK
            pass
        else:
            self.warning(msg='not send yet (type=%d): %s' % (content.type, receiver))
        return i_msg, r_msg

    async def send_instant_message(self, msg: InstantMessage, priority: int = 0) -> Optional[ReliableMessage]:
        """ Send message """
        receiver = msg.receiver
        assert msg.content.get('data') is None, 'cannot send this message: %s' % msg
        self.info(msg='sending message (type=%d): %s -> %s' % (msg.content.type, msg.sender, receiver))
        if receiver.is_user:
            # send out directly
            return await self.messenger.send_instant_message(msg=msg, priority=priority)
        # send by group manager
        manager = SharedGroupManager()
        return await manager.send_instant_message(msg=msg, priority=priority)

    #
    #   Send file content asynchronously
    #   ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    #   Step 1: save origin data into a cache directory;
    #   Step 2: save instant message without 'content.data';
    #   Step 3: encrypt the data with password;
    #   Step 4: upload the encrypted data and get a download URL;
    #   Step 5: resend the instant message with the download URL.
    #

    async def send_file_content(self, content: FileContent,
                                sender: Optional[ID], receiver: ID, priority: int = 0) -> bool:
        """ Send file content """
        # check sender
        if sender is None:
            user = await self.current_user
            assert user is not None, 'failed to get current user'
            sender = user.identifier
        # check receiver
        if receiver.is_group:
            assert content.group is None or content.group == receiver, 'group ID error: %s, %s' % (receiver, content)
            content.group = receiver
        # check download URL
        if content.url is None:
            # file data not uploaded yet,
            # try to upload file data to get download URL,
            # and then pack a message with the URL and decrypt key to send
            return await self.handle_file_message(content=content, sender=sender, receiver=receiver, priority=priority)
        elif content.data is not None:
            # FIXME:
            # download URL found, so file data should not exist here
            return await self.handle_file_message(content=content, sender=sender, receiver=receiver, priority=priority)
        # this file content's data had already been uploaded (download URL exists),
        # so pack and send it out directly.
        envelope = Envelope.create(sender=sender, receiver=receiver)
        i_msg = InstantMessage.create(head=envelope, body=content)
        r_msg = await self.send_instant_message(msg=i_msg, priority=priority)
        if r_msg is not None or receiver.is_group:
            return True
        else:
            self.warning(msg='not send yet (type=%d): %s' % (content.type, receiver))
            return False

    # protected
    async def handle_file_message(self, content: FileContent, sender: ID, receiver: ID, priority: int = 0) -> bool:
        # check filename
        filename = content.filename
        if filename is None:
            self.error(msg='file content error: %s, %s' % (sender, content))
            return False
        # check file data
        data = content.data
        #
        #   Step 1: save origin data into a cache directory;
        #
        if data is None:
            data = await self.get_file_data(filename=filename)
            if data is None:
                self.error(msg='file content error: %s, %s' % (sender, content))
                return False
        elif await self.cache_file_data(data=data, filename=filename):
            # file data saved into a cache file, so
            # here we can remove it from the content.
            content.data = None
        else:
            self.error(msg='failed to cache file: %s, %d byte(s)' % (filename, len(data)))
            return False
        assert content.url is None, 'file content error: %s' % content.url
        # assert content.password is None, 'file content error: %s' % content.url
        #
        #   Step 2: save instant message without 'content.data';
        #
        envelope = Envelope.create(sender=sender, receiver=receiver)
        i_msg = InstantMessage.create(head=envelope, body=content)
        if await self.cache_instant_message(msg=i_msg):
            # save it temporary
            pass
        else:
            self.error(msg='failed to save message: %s' % i_msg)
            return False
        #
        #   Step 3: encrypt the data with password;
        #
        # password = await self.messenger.get_encrypt_key(msg=i_msg)
        password = content.password
        if isinstance(password, SymmetricKey):
            # if password exists, reuse it
            pass
        else:
            # generate a new password for each file content
            password = SymmetricKey.generate(algorithm=SymmetricKey.AES)
            # NOTICE: to avoid communication key leaks,
            #         here we should generate a new key to encrypt file data,
            #         because this key will be attached into file content,
            #         if this content is forwarded, there is a security risk.
            self.info(msg='generated new password to upload file: %s, %s, %s' % (sender, filename, password))
            assert password is not None, 'failed to generate AES key: %s' % sender
        encrypted = password.encrypt(data=data, extra=content.dictionary)
        #
        #   Step 4: upload the encrypted data and get a download URL;
        #   Step 5: resend the instant message with the download URL.
        #
        return await self.send_file_message(data=encrypted, filename=filename, password=password, msg=i_msg,
                                            content=content, sender=sender, receiver=receiver, priority=priority)

    # protected
    async def send_file_message(self, data: bytes, filename: str, password: SymmetricKey, msg: InstantMessage,
                                content: FileContent, sender: ID, receiver: ID, priority: int = 0):
        #
        #   Step 4: upload the encrypted data and get a download URL;
        #
        url = await self.upload_file_data(data=data, filename=filename, sender=sender)
        if url is None:
            self.error(msg='failed to upload: %s -> %s, %d byte(s)' % (content.filename, filename, len(data)))
            # TODO: mark message failed
            return False
        else:
            self.info(msg='uploaded filename: %s -> %s => %s' % (content.filename, filename, url))
            content.url = url
            content.password = password
        #
        #   Step 5: resend the instant message with the download URL.
        #
        r_msg = await self.send_instant_message(msg=msg, priority=priority)
        if r_msg is not None or receiver.is_group:
            return True
        else:
            self.warning(msg='not send yet (type=%d): %s' % (content.type, receiver))
            return False

    @abstractmethod
    async def cache_file_data(self, data: bytes, filename: str) -> bool:
        """ Save origin file data into the cache """
        raise NotImplemented

    @abstractmethod
    async def get_file_data(self, filename: str) -> Optional[bytes]:
        """ Load origin file data from the cache """
        raise NotImplemented

    @abstractmethod
    async def cache_instant_message(self, msg: InstantMessage) -> bool:
        """ Save instant message without 'content.data' """
        raise NotImplemented

    @abstractmethod
    async def upload_file_data(self, data: bytes, filename: str, sender: ID) -> Optional[URI]:
        """
        Upload file data to CDN server

        :param data:     encrypted data
        :param filename: original filename
        :param sender:   sender ID
        :return: None on error
        """
        raise NotImplemented
