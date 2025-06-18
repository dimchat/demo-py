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
from .conn import *
from .database import *
from .group import *

from .emitter import Emitter


name = 'DIMPLES'

__author__ = 'Albert Moky'


__all__ = [

    'Emitter',

    ####################################
    #
    #   SDK
    #
    ####################################

    'Singleton',

    'URI', 'DateTime',

    'Converter', 'Copier',
    'Wrapper', 'Stringer', 'Mapper',
    'ConstantString',  # 'String',
    'Dictionary',

    #
    #   Data Format
    #

    'DataCoder', 'Hex', 'Base58', 'Base64',
    'ObjectCoder', 'JSON',
    'MapCoder', 'JSONMap',
    'ListCoder', 'JSONList',
    'StringCoder', 'UTF8',

    'hex_encode', 'hex_decode',
    'base58_encode', 'base58_decode',
    'base64_encode', 'base64_decode',
    'json_encode', 'json_decode',
    'utf8_encode', 'utf8_decode',

    'TransportableData', 'TransportableDataFactory',
    'PortableNetworkFile', 'PortableNetworkFileFactory',

    #
    #   Data Digest
    #

    'DataDigester',
    'MD5', 'SHA1', 'SHA256', 'KECCAK256', 'RIPEMD160',
    'md5', 'sha1', 'sha256', 'keccak256', 'ripemd160',

    #
    #   Crypto Keys
    #

    'CryptographyKey',
    'EncryptKey', 'DecryptKey', 'SignKey', 'VerifyKey',
    'SymmetricKey', 'AsymmetricKey',
    'PrivateKey', 'PublicKey',

    'SymmetricKeyFactory', 'PrivateKeyFactory', 'PublicKeyFactory',

    'BaseKey', 'BaseSymmetricKey',
    'BaseAsymmetricKey', 'BasePublicKey', 'BasePrivateKey',

    'BaseDataWrapper',
    'BaseFileWrapper',

    #
    #   MingKeMing
    #

    'EntityType',
    'Address',
    'ID',
    'Meta',
    'Document', 'Visa', 'Bulletin',

    'AddressFactory',
    'IDFactory',
    'MetaFactory',
    'DocumentFactory',

    'Identifier',
    'ANYONE', 'EVERYONE', 'FOUNDER',
    'ANYWHERE', 'EVERYWHERE',
    # 'BroadcastAddress',

    'BaseMeta',
    'BaseDocument', 'BaseVisa', 'BaseBulletin',

    #
    #   DaoKeDao
    #

    'ContentType',
    'Content',
    'Envelope',
    'Message',
    'InstantMessage', 'SecureMessage', 'ReliableMessage',

    # contents
    'TextContent', 'ArrayContent', 'ForwardContent',
    'PageContent', 'NameCard',
    'FileContent', 'ImageContent', 'AudioContent', 'VideoContent',
    'MoneyContent', 'TransferContent',
    'QuoteContent', 'CombineContent',

    # commands
    'Command',
    'MetaCommand', 'DocumentCommand',
    'ReceiptCommand',

    # group history
    'HistoryCommand', 'GroupCommand',
    'InviteCommand', 'ExpelCommand', 'JoinCommand', 'QuitCommand', 'QueryCommand', 'ResetCommand',
    'HireCommand', 'FireCommand', 'ResignCommand',

    # extend contents
    'BaseContent',
    'BaseTextContent', 'ListContent', 'SecretContent',
    'WebPageContent', 'NameCardContent',
    'BaseFileContent', 'ImageFileContent', 'AudioFileContent', 'VideoFileContent',
    'BaseMoneyContent', 'TransferMoneyContent',
    'BaseQuoteContent', 'CombineForwardContent',

    # extend commands
    'BaseCommand',
    'BaseMetaCommand', 'BaseDocumentCommand',
    'BaseReceiptCommand',

    # extend group history
    'BaseHistoryCommand', 'BaseGroupCommand',
    'InviteGroupCommand', 'ExpelGroupCommand', 'JoinGroupCommand',
    'QuitGroupCommand', 'QueryGroupCommand', 'ResetGroupCommand',
    'HireGroupCommand', 'FireGroupCommand', 'ResignGroupCommand',

    #
    #   Message
    #

    'MessageEnvelope',
    'BaseMessage',
    'PlainMessage', 'EncryptedMessage', 'NetworkMessage',

    # factories
    'ContentFactory', 'CommandFactory',
    'EnvelopeFactory',
    'InstantMessageFactory', 'SecureMessageFactory', 'ReliableMessageFactory',

    # delegates
    'InstantMessageDelegate', 'SecureMessageDelegate', 'ReliableMessageDelegate',

    #
    #   Core
    #

    'Barrack', 'Transceiver', 'Packer', 'Processor',
    'CipherKeyDelegate',

    #
    #   MingKeMing extends
    #

    'EntityDelegate',
    'Entity', 'EntityDataSource', 'BaseEntity',
    'User', 'UserDataSource', 'BaseUser',
    'Group', 'GroupDataSource', 'BaseGroup',

    'ServiceProvider', 'Station', 'Bot',

    'MemberType',

    'MetaUtils', 'DocumentUtils',

    #
    #   DaoKeDao extends
    #

    'ContentProcessor',
    'ContentProcessorCreator',
    'ContentProcessorFactory',
    'GeneralContentProcessorFactory',

    'GeneralCommandFactory',
    'HistoryCommandFactory',
    'GroupCommandFactory',

    'InstantMessagePacker', 'SecureMessagePacker', 'ReliableMessagePacker',
    'MessageFactory', 'MessageUtils',

    #
    #   Core extends
    #

    'TwinsHelper',

    'AddressNameService',
    'Archivist',
    'Facebook', 'Messenger',
    'MessageProcessor', 'MessagePacker',

    ####################################
    #
    #   SDK CPU
    #
    ####################################

    'ContentProcessor',
    'ContentProcessorCreator',
    'ContentProcessorFactory',
    'GeneralContentProcessorFactory',

    'BaseContentProcessor',
    'BaseCommandProcessor',

    'ArrayContentProcessor',
    'ForwardContentProcessor',

    'MetaCommandProcessor',
    'DocumentCommandProcessor',

    'BaseContentProcessorCreator',

    ####################################
    #
    #   Plugins
    #
    ####################################

    'Base64Coder', 'Base58Coder', 'HexCoder',
    'JSONCoder', 'UTF8Coder',

    'Base64Data', 'Base64DataFactory',
    'BaseNetworkFile', 'BaseNetworkFileFactory',

    #
    #   Digest
    #

    'MD5Digester', 'SHA1Digester', 'SHA256Digester',
    'Keccak256Digester', 'RipeMD160Digester',

    #
    #   Crypto
    #

    'PlainKey', 'PlainKeyFactory',
    'AESKey', 'AESKeyFactory',

    'RSAPublicKey', 'RSAPublicKeyFactory',
    'RSAPrivateKey', 'RSAPrivateKeyFactory',

    'ECCPublicKey', 'ECCPublicKeyFactory',
    'ECCPrivateKey', 'ECCPrivateKeyFactory',

    #
    #   MingKeMing
    #

    'BTCAddress', 'ETHAddress',
    'BaseAddressFactory',

    'GeneralIdentifierFactory',

    'DefaultMeta', 'BTCMeta', 'ETHMeta',
    'BaseMetaFactory',

    'GeneralDocumentFactory',

    #
    #   Loader
    #

    'PluginLoader',

    ####################################
    #
    #   Common
    #
    ####################################

    'MetaType',
    'Password',
    'BroadcastUtils',

    #
    #   protocol
    #

    'AnsCommand',

    'HandshakeCommand', 'HandshakeState',
    'LoginCommand',

    'BlockCommand',
    'MuteCommand',

    'ReportCommand',

    'GroupKeyCommand',

    'CustomizedContent', 'AppCustomizedContent',

    #
    #   Database Interface
    #

    'PrivateKeyDBI', 'MetaDBI', 'DocumentDBI',
    'UserDBI', 'ContactDBI', 'GroupDBI', 'GroupHistoryDBI',
    'AccountDBI',

    'ReliableMessageDBI', 'CipherKeyDBI', 'GroupKeysDBI',
    'MessageDBI',

    'ProviderDBI', 'StationDBI', 'LoginDBI',
    'SessionDBI',

    'ProviderInfo', 'StationInfo',

    #
    #   common
    #

    'Anonymous',
    'AddressNameServer', 'ANSFactory',

    'EntityChecker',
    'CommonArchivist',
    'CommonFacebook',

    'CommonMessenger',
    'CommonMessagePacker',
    'CommonMessageProcessor',
    'SuspendedMessageQueue',

    'Transmitter',
    'Session',

    'Register',

    ####################################
    #
    #   Connection
    #
    ####################################

    'Hub', 'Channel',
    'Connection', 'ConnectionDelegate', 'ConnectionState',
    'BaseChannel',
    'BaseHub', 'BaseConnection', 'ActiveConnection',

    'Ship', 'Arrival', 'Departure', 'DeparturePriority',
    'Porter', 'PorterStatus', 'PorterDelegate', 'Gate',
    'ArrivalShip', 'ArrivalHall', 'DepartureShip', 'DepartureHall',
    'Dock', 'LockedDock', 'StarPorter', 'StarGate',

    #
    #   TCP
    #
    'PlainArrival', 'PlainDeparture', 'PlainPorter',
    'StreamChannel', 'StreamHub', 'TCPServerHub', 'TCPClientHub',

    #
    #   UDP
    #
    'PackageArrival', 'PackageDeparture', 'PackagePorter',
    'PacketChannel', 'PacketHub', 'UDPServerHub', 'UDPClientHub',

    #
    #   Protocol
    #
    'WebSocket', 'NetMsg', 'NetMsgHead', 'NetMsgSeq',

    #
    #   Network
    #
    'WSArrival', 'WSDeparture', 'WSPorter',
    'MarsStreamArrival', 'MarsStreamDeparture', 'MarsStreamPorter',
    'MTPStreamArrival', 'MTPStreamDeparture', 'MTPStreamPorter',
    'FlexiblePorter',
    'CommonGate', 'TCPServerGate', 'TCPClientGate', 'UDPServerGate', 'UDPClientGate',
    # 'GateKeeper',
    'MessageWrapper', 'MessageQueue',
    'BaseSession',

    ####################################
    #
    #   Database
    #
    ####################################

    'PrivateKeyDBI', 'MetaDBI', 'DocumentDBI',
    'UserDBI', 'ContactDBI', 'GroupDBI', 'GroupHistoryDBI',
    'AccountDBI',

    'ReliableMessageDBI', 'CipherKeyDBI', 'GroupKeysDBI',
    'MessageDBI',

    'ProviderDBI', 'StationDBI', 'LoginDBI',
    'SessionDBI',
    'ProviderInfo', 'StationInfo',

    #
    #   DOS
    #

    'Storage',
    'PrivateKeyStorage', 'MetaStorage', 'DocumentStorage',
    'UserStorage', 'GroupStorage', 'GroupHistoryStorage',
    'GroupKeysStorage',
    'LoginStorage',
    'StationStorage',

    #
    #   Redis
    #

    'RedisConnector', 'RedisCache',

    'MetaCache', 'DocumentCache',
    'UserCache', 'LoginCache',
    'GroupCache', 'GroupHistoryCache', 'GroupKeysCache',
    'MessageCache',
    'StationCache',

    #
    #   Table
    #

    'DbTask', 'DataCache',

    'PrivateKeyTable', 'MetaTable', 'DocumentTable',
    'UserTable', 'GroupTable', 'GroupHistoryTable',
    'GroupKeysTable',
    'ReliableMessageTable', 'CipherKeyTable',
    'LoginTable', 'StationTable',

    #
    #   Database
    #

    'AccountDatabase',
    'MessageDatabase',
    'SessionDatabase',

    ####################################
    #
    #   Group
    #
    ####################################

    'TripletsHelper',
    # 'GroupBotsManager',

    'GroupDelegate',
    'GroupPacker',
    'GroupEmitter',

    'GroupCommandHelper',
    'GroupHistoryBuilder',

    'GroupManager',
    'AdminManager',

    'SharedGroupManager',

]
