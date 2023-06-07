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
from typing import Optional, Tuple

from dimsdk import Address, ID, IDFactory

from ..utils import Singleton
from ..common import AddressNameServer, CommonFacebook
from ..common import AccountDBI, MessageDBI, SessionDBI
from ..common import ProviderInfo
from ..database import AccountDatabase, MessageDatabase, SessionDatabase
from ..database import Storage
from ..server import Pusher, DefaultPusher, PushCenter
from ..server import Dispatcher

from ..config import Config


class ANSFactory(IDFactory):

    def __init__(self, factory: IDFactory, ans: AddressNameServer):
        super().__init__()
        self.__origin = factory
        self.__ans = ans

    # Override
    def generate_id(self, meta, network: int, terminal: Optional[str] = None) -> ID:
        return self.__origin.generate_id(meta=meta, network=network, terminal=terminal)

    # Override
    def create_id(self, name: Optional[str], address: Address, terminal: Optional[str] = None) -> ID:
        return self.__origin.create_id(address=address, name=name, terminal=terminal)

    # Override
    def parse_id(self, identifier: str) -> Optional[ID]:
        # try ANS record
        aid = self.__ans.identifier(name=identifier)
        if aid is None:
            # parse by original factory
            aid = self.__origin.parse_id(identifier=identifier)
        return aid


@Singleton
class GlobalVariable:

    def __init__(self):
        super().__init__()
        self.config: Optional[Config] = None
        self.adb: Optional[AccountDBI] = None
        self.mdb: Optional[MessageDBI] = None
        self.sdb: Optional[SessionDBI] = None
        self.facebook: Optional[CommonFacebook] = None
        self.pusher: Optional[Pusher] = None


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


def create_config(app_name: str, default_config: str) -> Config:
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
    if not Storage.exists(path=ini_file):
        show_help(cmd=cmd, app_name=app_name, default_config=default_config)
        print('')
        print('!!! config file not exists: %s' % ini_file)
        print('')
        sys.exit(0)
    # load config from file
    config = Config.load(file=ini_file)
    print('>>> config loaded: %s => %s' % (ini_file, config))
    return config


def create_database(config: Config) -> Tuple[AccountDBI, MessageDBI, SessionDBI]:
    """ Step 2: create database """
    root = config.database_root
    public = config.database_public
    private = config.database_private
    # create database
    adb = AccountDatabase(root=root, public=public, private=private)
    mdb = MessageDatabase(root=root, public=public, private=private)
    sdb = SessionDatabase(root=root, public=public, private=private)
    adb.show_info()
    mdb.show_info()
    sdb.show_info()
    # default provider
    provider = ProviderInfo.GSP
    # add neighbors
    neighbors = config.neighbors
    for node in neighbors:
        print('adding neighbor node: %s' % node)
        sdb.add_station(identifier=None, host=node.host, port=node.port, provider=provider)
    return adb, mdb, sdb


def create_facebook(database: AccountDBI, current_user: ID) -> CommonFacebook:
    """ Step 3: create facebook """
    facebook = CommonFacebook(database=database)
    # make sure private keys exists
    sign_key = facebook.private_key_for_visa_signature(identifier=current_user)
    msg_keys = facebook.private_keys_for_decryption(identifier=current_user)
    assert sign_key is not None, 'failed to get sign key for current user: %s' % current_user
    assert msg_keys is not None and len(msg_keys) > 0, 'failed to get msg keys: %s' % current_user
    print('set current user: %s' % current_user)
    facebook.current_user = facebook.user(identifier=current_user)
    return facebook


def create_ans(config: Config) -> AddressNameServer:
    """ Step 4: create ANS """
    ans = AddressNameServer()
    factory = ID.factory()
    ID.register(factory=ANSFactory(factory=factory, ans=ans))
    # load ANS records from 'config.ini'
    ans_records = config.ans_records
    if ans_records is not None:
        ans.fix(records=ans_records)
    return ans


def create_pusher(shared: GlobalVariable) -> Pusher:
    """ Step 5: create pusher """
    pusher = DefaultPusher(facebook=shared.facebook)
    shared.pusher = pusher
    # start PushCenter
    center = PushCenter()
    # TODO: add push services
    center.start()
    return pusher


def create_dispatcher(shared: GlobalVariable) -> Dispatcher:
    """ Step 6: create dispatcher """
    dispatcher = Dispatcher()
    dispatcher.mdb = shared.mdb
    dispatcher.sdb = shared.sdb
    dispatcher.facebook = shared.facebook
    dispatcher.pusher = shared.pusher
    dispatcher.start()
    return dispatcher
