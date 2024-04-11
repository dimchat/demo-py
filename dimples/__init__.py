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
from dimsdk.cpu import *
from dimplugins import *

from .common import *
from .group import *

name = 'DIMPLES'

__author__ = 'Albert Moky'


__all__ = [

    #
    #   Types
    #

    'URI', 'DateTime',
    'Converter',
    'Wrapper', 'Stringer', 'Mapper',
    'ConstantString',  # 'String',
    'Dictionary',

    #
    #   Data Format
    #

    'DataCoder', 'Hex', 'Base64', 'Base58',
    'ObjectCoder', 'JSON', 'MapCoder', 'JSONMap', 'ListCoder', 'JSONList',
    'StringCoder', 'UTF8',

    'hex_encode', 'hex_decode',
    'base64_encode', 'base64_decode', 'base58_encode', 'base58_decode',
    'json_encode', 'json_decode',
    'utf8_encode', 'utf8_decode',

    'TransportableData', 'TransportableDataFactory',
    'PortableNetworkFile', 'PortableNetworkFileFactory',
    'FormatGeneralFactory', 'FormatFactoryManager',

    #
    #   Data Digest
    #

    'DataDigester',
    'MD5', 'SHA1', 'SHA256', 'KECCAK256', 'RIPEMD160',
    'md5', 'sha1', 'sha256', 'keccak256', 'ripemd160',

    #
    #   Crypto Keys
    #

    'CryptographyKey', 'EncryptKey', 'DecryptKey',
    'AsymmetricKey', 'SignKey', 'VerifyKey',
    'SymmetricKey', 'SymmetricKeyFactory',
    'PublicKey', 'PublicKeyFactory',
    'PrivateKey', 'PrivateKeyFactory',

    'CryptographyKeyGeneralFactory', 'CryptographyKeyFactoryManager',

    #
    #   MingKeMing
    #

    'EntityType', 'MetaType',
    'Address', 'AddressFactory',
    'ID', 'IDFactory',
    'Meta', 'MetaFactory',
    # 'TAI',
    'Document', 'DocumentFactory',
    'Visa', 'Bulletin',

    'BroadcastAddress', 'Identifier',
    'AccountGeneralFactory', 'AccountFactoryManager',
    'ANYWHERE', 'EVERYWHERE', 'ANYONE', 'EVERYONE', 'FOUNDER',

    #
    #   DaoKeDao
    #

    'ContentType', 'Content', 'ContentFactory',
    'Envelope', 'EnvelopeFactory',
    'Message', 'InstantMessage', 'SecureMessage', 'ReliableMessage',
    'InstantMessageFactory', 'SecureMessageFactory', 'ReliableMessageFactory',

    'InstantMessageDelegate', 'SecureMessageDelegate', 'ReliableMessageDelegate',
    'MessageGeneralFactory', 'MessageFactoryManager',

    #
    #   Crypto core
    #

    'BaseKey', 'BaseSymmetricKey',
    'BaseAsymmetricKey', 'BasePublicKey', 'BasePrivateKey',

    'BaseDataWrapper',
    'BaseFileWrapper',

    #
    #   MingKeMing core
    #

    'BaseMeta', 'MetaHelper',
    'BaseDocument', 'BaseVisa', 'BaseBulletin', 'DocumentHelper',

    'EntityDelegate',
    'Entity', 'EntityDataSource', 'BaseEntity',
    'User', 'UserDataSource', 'BaseUser',
    'Group', 'GroupDataSource', 'BaseGroup',

    #
    #   Protocol core
    #

    'TextContent', 'ArrayContent', 'ForwardContent',
    'PageContent', 'NameCard',
    'FileContent', 'ImageContent', 'AudioContent', 'VideoContent',
    'MoneyContent', 'TransferContent',
    'CustomizedContent',

    'Command', 'CommandFactory',
    'MetaCommand', 'DocumentCommand',
    'ReceiptCommand', 'ReceiptCommandMixIn',

    'HistoryCommand', 'GroupCommand',
    'InviteCommand', 'ExpelCommand', 'JoinCommand', 'QuitCommand', 'QueryCommand', 'ResetCommand',
    'HireCommand', 'FireCommand', 'ResignCommand',

    #
    #   DaoKeDao core
    #

    'BaseContent',
    'BaseTextContent', 'ListContent', 'SecretContent',
    'WebPageContent', 'NameCardContent',
    'BaseFileContent', 'ImageFileContent', 'AudioFileContent', 'VideoFileContent',
    'BaseMoneyContent', 'TransferMoneyContent',
    'AppCustomizedContent',

    'BaseCommand',
    'BaseMetaCommand', 'BaseDocumentCommand',
    'BaseReceipt', 'BaseReceiptCommand',

    'BaseHistoryCommand', 'BaseGroupCommand',
    'InviteGroupCommand', 'ExpelGroupCommand', 'JoinGroupCommand',
    'QuitGroupCommand', 'QueryGroupCommand', 'ResetGroupCommand',
    'HireGroupCommand', 'FireGroupCommand', 'ResignGroupCommand',

    'CommandGeneralFactory', 'CommandFactoryManager',

    'MessageEnvelope', 'BaseMessage',
    'PlainMessage', 'EncryptedMessage', 'NetworkMessage',

    #
    #   Core
    #

    'Barrack', 'Transceiver', 'Packer', 'Processor',

    #
    #   MingKeMing extends
    #

    'ServiceProvider', 'Station', 'Bot',

    #
    #   DaoKeDao extends
    #

    'InstantMessagePacker', 'SecureMessagePacker', 'ReliableMessagePacker',
    'MessageFactory',

    #
    #   Core extends
    #

    'TwinsHelper',

    'ContentProcessor', 'ContentProcessorCreator', 'ContentProcessorFactory',
    'GeneralContentProcessorFactory',

    'ContentFactoryBuilder', 'CommandFactoryBuilder',
    'GeneralCommandFactory', 'HistoryCommandFactory', 'GroupCommandFactory',

    'register_content_factories', 'register_command_factories',
    'register_message_factories', 'register_all_factories',

    #
    #   Extends
    #

    'AddressNameService', 'CipherKeyDelegate',
    'Archivist',
    'Facebook', 'Messenger',
    'MessageProcessor', 'MessagePacker',

    ####################################
    #
    #   SDK CPU
    #
    ####################################

    'ContentProcessor', 'ContentProcessorCreator', 'ContentProcessorFactory',
    'GeneralContentProcessorFactory',

    'BaseContentProcessor', 'BaseCommandProcessor',

    'ForwardContentProcessor',
    'ArrayContentProcessor',

    'MetaCommandProcessor',
    'DocumentCommandProcessor',

    'CustomizedContentProcessor',
    'CustomizedContentHandler',

    'BaseContentProcessorCreator',

    ####################################
    #
    #   Plugins
    #
    ####################################

    'Base64Data', 'Base64DataFactory',
    'BaseNetworkFile', 'BaseNetworkFileFactory',

    'register_data_coders',

    #
    #   Crypto
    #

    'PlainKey', 'PlainKeyFactory',
    'AESKey', 'AESKeyFactory',

    'RSAPublicKey', 'RSAPublicKeyFactory',
    'RSAPrivateKey', 'RSAPrivateKeyFactory',

    'ECCPublicKey', 'ECCPublicKeyFactory',
    'ECCPrivateKey', 'ECCPrivateKeyFactory',

    'register_data_digesters',
    'register_symmetric_key_factories',
    'register_asymmetric_key_factories',

    #
    #   MingKeMing
    #

    'BTCAddress', 'ETHAddress',
    'DefaultMeta', 'BTCMeta', 'ETHMeta',

    'BaseAddressFactory', 'GeneralAddressFactory',
    'GeneralIdentifierFactory',
    'GeneralMetaFactory',
    'GeneralDocumentFactory',

    'register_address_factory',
    'register_identifier_factory',
    'register_meta_factories',
    'register_document_factories',

    #
    #   Register
    #

    'register_plugins',

    ####################################
    #
    #   Common
    #
    ####################################

    'HandshakeCommand', 'HandshakeState',
    'LoginCommand',
    'ReportCommand',
    'AnsCommand',

    'BlockCommand',
    'MuteCommand',

    #
    #   Database Interface
    #
    'PrivateKeyDBI', 'MetaDBI', 'DocumentDBI',
    'UserDBI', 'ContactDBI', 'GroupDBI', 'GroupHistoryDBI',
    'AccountDBI',

    'ReliableMessageDBI', 'CipherKeyDBI', 'GroupKeysDBI',
    'MessageDBI',

    'LoginDBI', 'ProviderDBI', 'StationDBI',
    'SessionDBI',
    'ProviderInfo', 'StationInfo',

    #
    #   common
    #
    'Anonymous', 'Register',
    'AddressNameServer', 'ANSFactory',
    'CommonArchivist',
    'CommonFacebook', 'CommonMessenger',
    'CommonMessagePacker', 'CommonMessageProcessor',
    'Transmitter',
    'Session',

    ####################################
    #
    #   Group
    #
    ####################################

    'GroupDelegate', 'GroupPacker', 'GroupEmitter',
    'GroupCommandHelper', 'GroupHistoryBuilder',
    'GroupManager', 'AdminManager',

]
