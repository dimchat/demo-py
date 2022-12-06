# -*- coding: utf-8 -*-
#
#   DIMPLES : DIMP Library for Edges and Stations
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

from mkm.types import *
from mkm.protocol import *
from dkd.protocol import *
from dimsdk import *
from dimplugins import *
from dimplugins.factories import *
from dimplugins.network import NetworkType
from dimplugins.entity import EntityID, EntityIDFactory

from .common import *
from .config import Config

name = 'DIMPLES'

__author__ = 'Albert Moky'


__all__ = [

    #
    #   Types
    #
    'Wrapper', 'Stringer', 'Mapper',
    'ConstantString',
    'Dictionary',

    #
    #   Crypto
    #
    'DataCoder', 'ObjectCoder', 'StringCoder',
    'Base64', 'Base58', 'Hex', 'JSON', 'UTF8',
    'base64_encode', 'base64_decode', 'base58_encode', 'base58_decode',
    'hex_encode', 'hex_decode',
    'json_encode', 'json_decode', 'utf8_encode', 'utf8_decode',

    'DataDigester',
    'MD5', 'SHA1', 'SHA256', 'KECCAK256', 'RIPEMD160',
    'md5', 'sha1', 'sha256', 'keccak256', 'ripemd160',

    'CryptographyKey',
    'SymmetricKey', 'EncryptKey', 'DecryptKey',
    'SymmetricKeyFactory',
    'AsymmetricKey', 'SignKey', 'VerifyKey',
    'PublicKey', 'PublicKeyFactory',
    'PrivateKey', 'PrivateKeyFactory',

    #
    #   MingKeMing
    #
    'EntityType', 'MetaType',
    'Address', 'AddressFactory',
    'ID', 'IDFactory',
    'Meta', 'MetaFactory',
    'Document', 'DocumentFactory',
    'Visa', 'Bulletin',

    'entity_is_user', 'entity_is_group', 'entity_is_broadcast',
    'meta_has_seed', 'meta_type',
    'document_type',

    'ANYWHERE', 'EVERYWHERE', 'ANYONE', 'EVERYONE', 'FOUNDER',

    'BaseAddressFactory', 'BroadcastAddress',
    'IdentifierFactory', 'Identifier',
    'BaseMeta',
    'BaseDocument', 'BaseVisa', 'BaseBulletin',

    #
    #   DaoKeDao
    #
    'ContentType', 'Content', 'ContentFactory',
    'Envelope', 'EnvelopeFactory',
    'Message', 'InstantMessage', 'SecureMessage', 'ReliableMessage',
    'InstantMessageFactory', 'SecureMessageFactory', 'ReliableMessageFactory',
    'InstantMessageDelegate', 'SecureMessageDelegate', 'ReliableMessageDelegate',

    'content_type',

    'BaseContent',
    'MessageEnvelope', 'MessageEnvelopeFactory',
    'BaseMessage',
    'PlainMessage', 'PlainMessageFactory',
    'EncryptedMessage', 'EncryptedMessageFactory',
    'NetworkMessage', 'NetworkMessageFactory',

    #
    #   DIMP
    #
    'TextContent', 'ForwardContent', 'ArrayContent',
    'MoneyContent', 'TransferContent',
    'FileContent', 'ImageContent', 'AudioContent', 'VideoContent',
    'PageContent', 'CustomizedContent',
    'Command', 'CommandFactory',
    'MetaCommand', 'DocumentCommand',
    'HistoryCommand', 'GroupCommand',
    'InviteCommand', 'ExpelCommand', 'JoinCommand',
    'QuitCommand', 'QueryCommand', 'ResetCommand',

    'EntityDelegate',
    'EntityDataSource', 'UserDataSource', 'GroupDataSource',
    'Entity', 'User', 'Group',
    'BaseEntity', 'BaseUser', 'BaseGroup',

    'BaseTextContent', 'SecretContent', 'ListContent',
    'BaseMoneyContent', 'TransferMoneyContent',
    'BaseFileContent', 'ImageFileContent', 'AudioFileContent', 'VideoFileContent',
    'WebPageContent', 'AppCustomizedContent',
    'BaseCommand', 'BaseMetaCommand', 'BaseDocumentCommand',
    'BaseHistoryCommand', 'BaseGroupCommand',
    'InviteGroupCommand', 'ExpelGroupCommand', 'JoinGroupCommand',
    'QuitGroupCommand', 'QueryGroupCommand', 'ResetGroupCommand',

    'ContentFactoryBuilder', 'CommandFactoryBuilder',
    'GeneralCommandFactory', 'HistoryCommandFactory', 'GroupCommandFactory',
    # register_core_factories
    'register_content_factories', 'register_command_factories',

    'Barrack', 'Transceiver', 'Packer', 'Processor',

    #
    #   Core
    #
    'ServiceProvider', 'Station', 'Bot',

    'AddressNameService', 'CipherKeyDelegate', 'TwinsHelper',
    'Facebook', 'Messenger', 'MessagePacker', 'MessageProcessor',
    'ContentProcessor', 'ContentProcessorFactory', 'ContentProcessorCreator',

    'ContentFactoryBuilder', 'CommandFactoryBuilder',
    'GeneralCommandFactory', 'HistoryCommandFactory', 'GroupCommandFactory',

    'register_content_factories', 'register_command_factories',
    'register_core_factories',

    #
    #   CPU
    #
    'BaseContentProcessorCreator', 'GeneralContentProcessorFactory',
    'BaseContentProcessor', 'BaseCommandProcessor',
    'ForwardContentProcessor', 'ArrayContentProcessor',
    'CustomizedContentProcessor', 'CustomizedContentHandler',
    'MetaCommandProcessor', 'DocumentCommandProcessor',
    'HistoryCommandProcessor', 'GroupCommandProcessor',
    'InviteCommandProcessor', 'ExpelCommandProcessor', 'QuitCommandProcessor',
    'ResetCommandProcessor', 'QueryCommandProcessor',

    #
    #   Plugins
    #
    'RSAPublicKey', 'RSAPrivateKey',
    'ECCPublicKey', 'ECCPrivateKey',
    'AESKey',
    'PlainKey',

    'GeneralPublicFactory', 'GeneralPrivateFactory',
    'GeneralSymmetricFactory',
    'GeneralAddressFactory',
    'GeneralMetaFactory',
    'GeneralDocumentFactory',

    'NetworkType',
    'EntityID', 'EntityIDFactory',

    'BTCAddress', 'ETHAddress',
    'DefaultMeta', 'BTCMeta', 'ETHMeta',

    #
    #   Extend Protocol
    #
    'HandshakeCommand', 'HandshakeState',
    'ReceiptCommand',
    'LoginCommand',
    'ReportCommand',

    #
    #   Database Interfaces
    #
    'PrivateKeyDBI', 'MetaDBI', 'DocumentDBI', 'UserDBI', 'GroupDBI',
    'AccountDBI',
    'ReliableMessageDBI', 'CipherKeyDBI',
    'MessageDBI',
    'LoginDBI', 'ProviderDBI',
    'SessionDBI',

    #
    #   Common
    #
    'FrequencyChecker', 'QueryFrequencyChecker',

    'CommonFacebook', 'CommonMessenger',
    'CommonProcessor', 'CommonContentProcessorCreator',
    'CommonPacker', 'Transmitter',
    'Session',

    'Config',
]
