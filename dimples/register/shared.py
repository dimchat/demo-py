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

from typing import Optional

from dimsdk import EntityType
from dimsdk import ID, Bulletin

from ..common.compat import NetworkType, network_to_type

from ..utils import Singleton, Config
from ..common import AccountDBI
from ..database import AccountDatabase


from .base import BaseAccount
from .ext import GroupAccount
from .ext import UserAccount, BotAccount, StationAccount


@Singleton
class GlobalVariable:

    def __init__(self):
        super().__init__()
        self.config: Optional[Config] = None
        self.adb: Optional[AccountDBI] = None


def create_database(shared: GlobalVariable) -> AccountDBI:
    config = shared.config
    root = config.database_root
    public = config.database_public
    private = config.database_private
    # create database
    adb = AccountDatabase(root=root, public=public, private=private)
    adb.show_info()
    shared.adb = adb
    return adb


def create_account(network: int, database: AccountDBI) -> BaseAccount:
    if EntityType.is_group(network=network_to_type(network=network)):
        return GroupAccount(database=database)
    elif network in [EntityType.STATION, NetworkType.STATION]:
        return StationAccount(database=database)
    elif network in [EntityType.BOT, NetworkType.BOT]:
        return BotAccount(database=database)
    else:
        return UserAccount(database=database)


def generate(database: AccountDBI):
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
        account.load_founder(founder=founder)
    account.generate(network=network, version=version, seed=seed)
    #
    #   Step 2. edit & save
    #
    account.update()
    account.show_info()


def modify(identifier: ID, database: AccountDBI):
    print('Modifying DIM account...')
    #
    #   Step 0: check meta & document
    #
    network = identifier.type
    #
    #   Step 1: create account
    #
    account = create_account(network=network, database=database)
    meta, doc = account.load_info(identifier=identifier)
    if isinstance(account, GroupAccount):
        assert isinstance(doc, Bulletin), 'group document error: %s' % doc
        founder = doc.founder
        assert founder is not None, 'founder not found: %s' % doc
        account.load_founder(founder=founder)
    #
    #   Step 2. edit & save
    #
    account.update()
    account.show_info()
