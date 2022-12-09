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

from ..utils import Singleton
from ..common import CommonFacebook
from ..common import AccountDBI, MessageDBI, SessionDBI
from ..database import AccountDatabase, MessageDatabase, SessionDatabase

from ..config import Config


@Singleton
class GlobalVariable:

    def __init__(self):
        super().__init__()
        self.config: Optional[Config] = None
        self.adb: Optional[AccountDBI] = None
        self.mdb: Optional[MessageDBI] = None
        self.sdb: Optional[SessionDBI] = None
        self.facebook: Optional[CommonFacebook] = None


def create_database(shared: GlobalVariable) -> (AccountDBI, MessageDBI, SessionDBI):
    config = shared.config
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
    shared.adb = adb
    shared.mdb = mdb
    shared.sdb = sdb
    # add neighbors
    neighbors = config.neighbors
    for node in neighbors:
        print('adding neighbor node: (%s:%d), ID=%s' % (node.host, node.port, node.identifier))
        sdb.add_neighbor(host=node.host, port=node.port)
    return adb, mdb, sdb


def create_facebook(shared: GlobalVariable) -> CommonFacebook:
    # set account database
    facebook = CommonFacebook(database=shared.adb)
    shared.facebook = facebook
    # set current station
    sid = shared.config.station_id
    if sid is not None:
        # make sure private key exists
        assert facebook.private_key_for_visa_signature(identifier=sid) is not None, \
            'failed to get sign key for current station: %s' % sid
        print('set current user: %s' % sid)
        facebook.current_user = facebook.user(identifier=sid)
    return facebook
