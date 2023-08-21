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

from dimsdk import *
from dimplugins import *

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

    'BroadcastAddress', 'Identifier',
    'ANYWHERE', 'EVERYWHERE', 'ANYONE', 'EVERYONE', 'FOUNDER',

    #
    #   MingKeMing base extends
    #
    'BaseMeta',
    'BaseDocument', 'BaseVisa', 'BaseBulletin',
    'BaseDocumentFactory',
    'BaseAddressFactory', 'IdentifierFactory',

    'EntityDelegate',
    'EntityDataSource', 'UserDataSource', 'GroupDataSource',
    'Entity', 'User', 'Group',
    'BaseEntity', 'BaseUser', 'BaseGroup',

    #
    #   DaoKeDao
    #
    'ContentType', 'Content', 'ContentFactory',
    'Envelope', 'EnvelopeFactory',
    'Message', 'InstantMessage', 'SecureMessage', 'ReliableMessage',
    'InstantMessageFactory', 'SecureMessageFactory', 'ReliableMessageFactory',
    'InstantMessageDelegate', 'SecureMessageDelegate', 'ReliableMessageDelegate',

    #
    #   DaoKeDao protocol extends
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

    #
    #   DaoKeDao base extends
    #
    'BaseContent',
    'BaseTextContent', 'SecretContent', 'ListContent',
    'BaseMoneyContent', 'TransferMoneyContent',
    'BaseFileContent', 'ImageFileContent', 'AudioFileContent', 'VideoFileContent',
    'WebPageContent', 'AppCustomizedContent',
    'BaseCommand',
    'BaseMetaCommand', 'BaseDocumentCommand',
    'BaseHistoryCommand', 'BaseGroupCommand',
    'InviteGroupCommand', 'ExpelGroupCommand', 'JoinGroupCommand',
    'QuitGroupCommand', 'QueryGroupCommand', 'ResetGroupCommand',

    # 'MessageEnvelope', 'MessageEnvelopeFactory',
    # 'BaseMessage',
    # 'PlainMessage', 'PlainMessageFactory',
    # 'EncryptedMessage', 'EncryptedMessageFactory',
    # 'NetworkMessage', 'NetworkMessageFactory',

    #
    #   Core
    #
    'Barrack', 'Transceiver', 'Packer', 'Processor',

    #
    #   Extends
    #
    'ServiceProvider', 'Station', 'Bot',

    'AddressNameService', 'CipherKeyDelegate',
    'Facebook', 'Messenger',
    'TwinsHelper',
    'ContentProcessor', 'ContentProcessorFactory', 'ContentProcessorCreator',
    'MessageProcessor', 'MessagePacker',

    'ContentFactoryBuilder', 'CommandFactoryBuilder',
    'GeneralCommandFactory', 'HistoryCommandFactory', 'GroupCommandFactory',

    # 'register_content_factories', 'register_command_factories',
    # 'register_message_factories',
    # 'register_all_factories',

    #
    #   CPU
    #
    'BaseContentProcessorCreator', 'GeneralContentProcessorFactory',
    'BaseContentProcessor', 'BaseCommandProcessor',
    'ForwardContentProcessor', 'ArrayContentProcessor',
    'CustomizedContentProcessor', 'CustomizedContentHandler',
    'MetaCommandProcessor', 'DocumentCommandProcessor',

    #
    #   Plugins
    #
    'BaseKey',
    'BaseSymmetricKey', 'BaseAsymmetricKey',
    'BasePublicKey', 'BasePrivateKey',

    'RSAPublicKey', 'RSAPrivateKey',
    'ECCPublicKey', 'ECCPrivateKey',
    'AESKey',
    'PlainKey',

    'RSAPublicKeyFactory', 'RSAPrivateKeyFactory',
    'ECCPublicKeyFactory', 'ECCPrivateKeyFactory',
    'AESKeyFactory', 'PlainKeyFactory',
    'GeneralAddressFactory',
    'GeneralMetaFactory',

    'NetworkType',
    'EntityID',
    'EntityIDFactory',

    'BTCAddress', 'ETHAddress',
    'DefaultMeta', 'BTCMeta', 'ETHMeta',

    # 'register_data_coders',
    # 'register_data_digesters',
    # 'register_symmetric_key_factories',
    # 'register_asymmetric_key_factories',
    # 'register_id_factory',
    # 'register_address_factory',
    # 'register_meta_factories',
    # 'register_document_factories',
    # 'register_plugins',

    #
    #   Common Protocol
    #
    'HandshakeCommand', 'HandshakeState',
    'ReceiptCommand',
    'LoginCommand',
    'ReportCommand',
    'AnsCommand',

    #
    #   Database Interfaces
    #
    'PrivateKeyDBI', 'MetaDBI', 'DocumentDBI', 'UserDBI', 'GroupDBI', 'ResetGroupDBI',
    'AccountDBI',
    'ReliableMessageDBI', 'CipherKeyDBI', 'GroupKeysDBI',
    'MessageDBI',
    'LoginDBI', 'ProviderDBI', 'StationDBI',
    'SessionDBI',
    'ProviderInfo', 'StationInfo',

    #
    #   Common Extends
    #
    'AddressNameServer',
    'CommonFacebook',
    'CommonMessenger',
    'CommonMessagePacker',
    'Transmitter',
    'Session',

    'Config',
]
