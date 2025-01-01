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

import getopt
import sys
from typing import Optional

from dimsdk import EntityType
from dimsdk import ID, Bulletin

from ..common.compat import NetworkType, network_to_type

from ..utils import Singleton, Config
from ..utils import Path
from ..common import AccountDBI
from ..common.compat import CommonLoader
from ..database.redis import RedisConnector
from ..database import DbInfo
from ..database import AccountDatabase


from .base import BaseAccount
from .ext import GroupAccount
from .ext import UserAccount, BotAccount, StationAccount


@Singleton
class GlobalVariable:

    def __init__(self):
        super().__init__()
        self.__config: Optional[Config] = None
        self.__adb: Optional[AccountDBI] = None

    @property
    def config(self) -> Config:
        return self.__config

    @property
    def adb(self) -> AccountDBI:
        return self.__adb

    async def prepare(self, default_config: str):
        #
        #  Step 1: load config
        #
        config = await create_config(default_config=default_config)
        self.__config = config
        #
        #  Step 2: create database
        #
        adb = await create_database(config=config)
        self.__adb = adb


def show_help(cmd: str, default_config: str):
    print('')
    print('    DIM account generate/modify')
    print('')
    print('usages:')
    print('    %s [--config=<FILE>] generate' % cmd)
    print('    %s [--config=<FILE>] modify <ID>' % cmd)
    print('    %s [-h|--help]' % cmd)
    print('')
    print('actions:')
    print('    generate        create new ID, meta & document')
    print('    modify <ID>     edit document with ID')
    print('')
    print('optional arguments:')
    print('    --config        config file path (default: "%s")' % default_config)
    print('    --help, -h      show this help message and exit')
    print('')


async def create_config(default_config: str) -> Config:
    """ Step 1: load config """
    cmd = sys.argv[0]
    try:
        opts, args = getopt.getopt(args=sys.argv[1:],
                                   shortopts='hf:',
                                   longopts=['help', 'config='])
    except getopt.GetoptError:
        show_help(cmd=cmd, default_config=default_config)
        sys.exit(1)
    # check options
    ini_file = None
    for opt, arg in opts:
        if opt == '--config':
            ini_file = arg
        else:
            show_help(cmd=cmd, default_config=default_config)
            sys.exit(0)
    # check config filepath
    if ini_file is None:
        ini_file = default_config
    if not await Path.exists(path=ini_file):
        show_help(cmd=cmd, default_config=default_config)
        print('')
        print('!!! config file not exists: %s' % ini_file)
        print('')
        sys.exit(0)
    # load extensions
    CommonLoader().run()
    # load config from file
    config = Config.load(file=ini_file)
    # initializing
    print('[DB] init with config: %s => %s' % (ini_file, config))
    # OK
    return config


def create_redis_connector(config: Config) -> Optional[RedisConnector]:
    redis_enable = config.get_boolean(section='redis', option='enable')
    if redis_enable:
        # create redis connector
        host = config.get_string(section='redis', option='host')
        if host is None:
            host = 'localhost'
        port = config.get_integer(section='redis', option='port')
        if port is None or port <= 0:
            port = 6379
        username = config.get_string(section='redis', option='username')
        password = config.get_string(section='redis', option='password')
        return RedisConnector(host=host, port=port, username=username, password=password)


async def create_database(config: Config) -> AccountDBI:
    """ Step 2: create database """
    root = config.database_root
    public = config.database_public
    private = config.database_private
    redis_conn = create_redis_connector(config=config)
    info = DbInfo(redis_connector=redis_conn, root_dir=root, public_dir=public, private_dir=private)
    # create database
    adb = AccountDatabase(info=info)
    adb.show_info()
    return adb


"""
    Functions
    ~~~~~~~~~
"""


def create_account(network: int, database: AccountDBI) -> BaseAccount:
    if EntityType.is_group(network=network_to_type(network=network)):
        return GroupAccount(database=database)
    elif network in [EntityType.STATION, NetworkType.STATION]:
        return StationAccount(database=database)
    elif network in [EntityType.BOT, NetworkType.BOT]:
        return BotAccount(database=database)
    else:
        return UserAccount(database=database)


async def generate(database: AccountDBI):
    print('Generating DIM account...')
    #
    #   Step 0. get entity type, meta type & meta seed (ID.name)
    #
    network = BaseAccount.get_address_type()
    version = BaseAccount.get_meta_type(address_type=network)
    seed = BaseAccount.get_meta_seed(meta_type=version, address_type=network)
    #
    #   Step 1. generate account
    #
    account = create_account(network=network, database=database)
    if isinstance(account, GroupAccount):
        founder = account.get_founder()
        assert founder is not None, 'failed to get founder'
        await account.load_founder(founder=founder)
    account.generate(network=network, version=version, seed=seed)
    #
    #   Step 2. edit & save
    #
    await account.update()
    account.show_info()


async def modify(identifier: ID, database: AccountDBI):
    print('Modifying DIM account...')
    #
    #   Step 0: check meta & document
    #
    network = identifier.type
    #
    #   Step 1: create account
    #
    account = create_account(network=network, database=database)
    meta, doc = await account.load_info(identifier=identifier)
    if isinstance(account, GroupAccount):
        assert isinstance(doc, Bulletin), 'group document error: %s' % doc
        founder = doc.founder
        assert founder is not None, 'founder not found: %s' % doc
        await account.load_founder(founder=founder)
    #
    #   Step 2. edit & save
    #
    await account.update()
    account.show_info()
