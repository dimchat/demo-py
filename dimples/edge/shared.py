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
import time
from typing import Optional, Tuple

from dimsdk import ID

from ..utils import Singleton, Config
from ..utils import Path
from ..common import AccountDBI, MessageDBI, SessionDBI
from ..common import ProviderInfo
from ..database.redis import RedisConnector
from ..database import DbInfo
from ..database import AccountDatabase, MessageDatabase, SessionDatabase
from ..client import ClientFacebook, ClientArchivist


@Singleton
class GlobalVariable:

    def __init__(self):
        super().__init__()
        self.config: Optional[Config] = None
        self.adb: Optional[AccountDBI] = None
        self.mdb: Optional[MessageDBI] = None
        self.sdb: Optional[SessionDBI] = None
        self.facebook: Optional[ClientFacebook] = None

    async def prepare(self, app_name: str, default_config: str):
        #
        #  Step 1: load config
        #
        config = await create_config(app_name=app_name, default_config=default_config)
        self.config = config
        #
        #  Step 2: create database
        #
        adb, mdb, sdb = await create_database(config=config)
        self.adb = adb
        self.mdb = mdb
        self.sdb = sdb
        #
        #  Step 3: create facebook
        #
        sid = config.station_id
        facebook = await create_facebook(database=adb, current_user=sid)
        self.facebook = facebook


def show_help(cmd: str, app_name: str, default_config: str):
    print('')
    print('    %s' % app_name)
    print('')
    print('usages:')
    print('    %s [--config=<FILE>]' % cmd)
    print('    %s [-h|--help]' % cmd)
    print('')
    print('optional arguments:')
    print('    --config        config file path (default: "%s")' % default_config)
    print('    --help, -h      show this help message and exit')
    print('')


async def create_config(app_name: str, default_config: str) -> Config:
    """ Step 1: load config """
    cmd = sys.argv[0]
    try:
        opts, args = getopt.getopt(args=sys.argv[1:],
                                   shortopts='hf:',
                                   longopts=['help', 'config='])
    except getopt.GetoptError:
        show_help(cmd=cmd, app_name=app_name, default_config=default_config)
        sys.exit(1)
    # check options
    ini_file = None
    for opt, arg in opts:
        if opt == '--config':
            ini_file = arg
        else:
            show_help(cmd=cmd, app_name=app_name, default_config=default_config)
            sys.exit(0)
    # check config filepath
    if ini_file is None:
        ini_file = default_config
    if not await Path.exists(path=ini_file):
        show_help(cmd=cmd, app_name=app_name, default_config=default_config)
        print('')
        print('!!! config file not exists: %s' % ini_file)
        print('')
        sys.exit(0)
    # load config from file
    config = Config.load(file=ini_file)
    print('>>> config loaded: %s => %s' % (ini_file, config))
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


async def create_database(config: Config) -> Tuple[AccountDBI, MessageDBI, SessionDBI]:
    """ Step 2: create database """
    root = config.database_root
    public = config.database_public
    private = config.database_private
    redis_conn = create_redis_connector(config=config)
    info = DbInfo(redis_connector=redis_conn, root_dir=root, public_dir=public, private_dir=private)
    # create database
    adb = AccountDatabase(info=info)
    mdb = MessageDatabase(info=info)
    sdb = SessionDatabase(info=info)
    adb.show_info()
    mdb.show_info()
    sdb.show_info()
    #
    #  Update neighbor stations (default provider)
    #
    provider = ProviderInfo.GSP
    neighbors = config.neighbors
    if len(neighbors) > 0:
        # await sdb.remove_stations(provider=provider)
        # 1. remove vanished neighbors
        old_stations = await sdb.all_stations(provider=provider)
        for old in old_stations:
            found = False
            for item in neighbors:
                if item.port == old.port and item.host == old.host:
                    found = True
                    break
            if not found:
                print('removing neighbor station: %s' % old)
                await sdb.remove_station(host=old.host, port=old.port, provider=provider)
        # 2. add new neighbors
        for node in neighbors:
            found = False
            for old in old_stations:
                if old.port == node.port and old.host == node.host:
                    found = True
                    break
            if not found:
                print('adding neighbor node: %s' % node)
                await sdb.add_station(identifier=None, host=node.host, port=node.port, provider=provider)
    return adb, mdb, sdb


def create_archivist(database: AccountDBI, facebook: ClientFacebook) -> ClientArchivist:
    archivist = ClientArchivist(database=database)
    archivist.facebook = facebook  # Weak Reference
    return archivist


async def create_facebook(database: AccountDBI, current_user: ID) -> ClientFacebook:
    """ Step 3: create facebook """
    facebook = ClientFacebook()
    # create archivist for facebook
    facebook.archivist = create_archivist(database=database, facebook=facebook)
    # make sure private keys exists
    sign_key = await facebook.private_key_for_visa_signature(identifier=current_user)
    msg_keys = await facebook.private_keys_for_decryption(identifier=current_user)
    assert sign_key is not None, 'failed to get sign key for current user: %s' % current_user
    assert len(msg_keys) > 0, 'failed to get msg keys: %s' % current_user
    print('set current user: %s' % current_user)
    user = await facebook.get_user(identifier=current_user)
    assert user is not None, 'failed to get current user: %s' % current_user
    visa = await user.visa
    if visa is not None:
        # refresh visa
        now = time.time()
        visa.set_property(name='time', value=now)
        visa.sign(private_key=sign_key)
        await facebook.save_document(document=visa)
    await facebook.set_current_user(user=user)
    return facebook
