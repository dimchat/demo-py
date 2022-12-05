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

from dimsdk import ID

from ..utils import Singleton
from ..common import CommonFacebook
from ..common import AccountDBI, MessageDBI, SessionDBI
from ..database import AccountDatabase, MessageDatabase, SessionDatabase
from ..server import Pusher, DefaultPusher, PushCenter
from ..server import Dispatcher
from ..server import UserDeliver, BotDeliver, StationDeliver
from ..server import GroupDeliver, BroadcastDeliver
from ..server import DeliverWorker, DefaultRoamer

from ..config import Config
from .ans import AddressNameService, AddressNameServer, ANSFactory


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


def init_database(shared: GlobalVariable):
    config = shared.config
    # create database
    adb = AccountDatabase(root=config.root, public=config.public, private=config.private)
    mdb = MessageDatabase(root=config.root, public=config.public, private=config.private)
    sdb = SessionDatabase(root=config.root, public=config.public, private=config.private)
    adb.show_info()
    mdb.show_info()
    sdb.show_info()
    shared.adb = adb
    shared.mdb = mdb
    shared.sdb = sdb
    # add neighbors
    neighbors = config.neighbors
    for node in neighbors:
        print('adding neighbor node: (%s:%d), ID="%s"' % (node.host, node.port, node.identifier))
        sdb.add_neighbor(host=node.host, port=node.port, identifier=node.identifier)


def init_facebook(shared: GlobalVariable) -> CommonFacebook:
    # set account database
    facebook = CommonFacebook()
    facebook.database = shared.adb
    shared.facebook = facebook
    # set current station
    station = shared.config.station
    if station is not None:
        # make sure private key exists
        assert facebook.private_key_for_visa_signature(identifier=station) is not None, \
            'failed to get sign key for current station: %s' % station
        print('set current user: %s' % station)
        facebook.current_user = facebook.user(identifier=station)
    return facebook


def init_ans(shared: GlobalVariable) -> AddressNameService:
    ans = AddressNameServer()
    factory = ID.factory()
    ID.register(factory=ANSFactory(factory=factory, ans=ans))
    # load ANS records from 'config.ini'
    config = shared.config
    ans.fix(fixed=config.ans_records)
    return ans


def init_pusher(shared: GlobalVariable) -> Pusher:
    pusher = DefaultPusher(facebook=shared.facebook)
    shared.pusher = pusher
    # start PushCenter
    center = PushCenter()
    # TODO: add push services
    center.start()
    return pusher


def init_dispatcher(shared: GlobalVariable) -> Dispatcher:
    # create dispatcher
    dispatcher = Dispatcher()
    dispatcher.database = shared.mdb
    dispatcher.facebook = shared.facebook
    # set base deliver delegates
    user_deliver = UserDeliver(database=shared.mdb, pusher=shared.pusher)
    bot_deliver = BotDeliver(database=shared.mdb)
    station_deliver = StationDeliver()
    dispatcher.set_user_deliver(deliver=user_deliver)
    dispatcher.set_bot_deliver(deliver=bot_deliver)
    dispatcher.set_station_deliver(deliver=station_deliver)
    # set special deliver delegates
    group_deliver = GroupDeliver(facebook=shared.facebook)
    broadcast_deliver = BroadcastDeliver(database=shared.sdb)
    dispatcher.set_group_deliver(deliver=group_deliver)
    dispatcher.set_broadcast_deliver(deliver=broadcast_deliver)
    # set roamer & worker
    roamer = DefaultRoamer(database=shared.mdb)
    worker = DeliverWorker(database=shared.sdb, facebook=shared.facebook)
    dispatcher.set_roamer(roamer=roamer)
    dispatcher.set_deliver_worker(worker=worker)
    # start all delegates
    user_deliver.start()
    bot_deliver.start()
    station_deliver.start()
    roamer.start()
    return dispatcher


# noinspection PyUnusedLocal
def stop_dispatcher(shared: GlobalVariable) -> bool:
    # stop Dispatcher
    dispatcher = Dispatcher()
    dispatcher.stop()
    return True


# noinspection PyUnusedLocal
def stop_pusher(shared: GlobalVariable) -> bool:
    # stop PushCenter
    center = PushCenter()
    center.stop()
    return True
