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

from configparser import ConfigParser
from configparser import NoSectionError, NoOptionError
from typing import Optional

from dimsdk import ID

from ..utils import json_encode
from ..utils import Singleton
from ..common import CommonFacebook
from ..common import AccountDBI, MessageDBI, SessionDBI
from ..database import AccountDatabase, MessageDatabase, SessionDatabase
from ..server import DefaultPusher, PushCenter
from ..server import Dispatcher, DefaultRoamer
from ..server import DefaultDeliver, GroupDeliver, BroadcastDeliver


class Config:

    def __init__(self, station: ID, host: str, port: int, root: str, public: str, private: str):
        super().__init__()
        self.station = station
        # server
        self.host = host
        self.port = port
        # database
        self.root = root
        self.public = public
        self.private = private

    def __str__(self) -> str:
        return self.to_json()

    def __repr__(self) -> str:
        return self.to_json()

    def to_json(self) -> str:
        info = {
            'station': str(self.station),
            'server': {
                'host': self.host,
                'port': self.port,
            },
            'database': {
                'root': self.root,
                'public': self.public,
                'private': self.private,
            },
        }
        return json_encode(obj=info)

    @classmethod
    def create(cls, station: ID = None, host: str = None, port: int = None,
               root: str = None, public: str = None, private: str = None):
        # server
        if host is None:
            host = '127.0.0.1'
        if port is None:
            port = 9394
        # database
        if root is None:
            root = '/var/.dim'
        if public is None:
            public = '%s/public' % root    # /var/.dim/public
        if private is None:
            private = '%s/private' % root  # /var/.dim/private
        # create
        return cls(station=station, host=host, port=port,
                   root=root, public=public, private=private)


class ConfigLoader:

    def __init__(self, file: str = None):
        super().__init__()
        parser = ConfigParser()
        parser.read(file)
        self.__parser = parser

    def _get_str(self, section: str, option: str) -> str:
        try:
            return self.__parser.get(section=section, option=option)
        except NoSectionError:
            pass
        except NoOptionError:
            pass

    def _get_int(self, section: str, option: str) -> int:
        try:
            return self.__parser.getint(section=section, option=option)
        except NoSectionError:
            pass
        except NoOptionError:
            pass

    def _get_bool(self, section: str, option: str) -> bool:
        try:
            return self.__parser.getboolean(section=section, option=option)
        except NoSectionError:
            pass
        except NoOptionError:
            pass

    def load(self) -> Config:
        #
        # 1. get options
        #
        station = self._get_str(section='ans', option='station')
        # server
        host = self._get_str(section='server', option='host')
        port = self._get_int(section='server', option='port')
        # database
        root = self._get_str(section='database', option='root')
        public = self._get_str(section='database', option='public')
        private = self._get_str(section='database', option='private')
        #
        # 2. check options
        #
        if station is not None:
            station = ID.parse(identifier=station)
        #
        # 3. create config
        #
        return Config.create(station=station, host=host, port=port,
                             root=root, public=public, private=private)


@Singleton
class GlobalVariable:

    def __init__(self):
        super().__init__()
        self.config: Optional[Config] = None
        self.adb: Optional[AccountDBI] = None
        self.mdb: Optional[MessageDBI] = None
        self.sdb: Optional[SessionDBI] = None


@Singleton
class SharedFacebook(CommonFacebook):
    pass


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


def init_facebook(shared: GlobalVariable) -> CommonFacebook:
    # set account database
    facebook = SharedFacebook()
    facebook.database = shared.adb
    # set current station
    station = shared.config.station
    if station is not None:
        print('set current user: %s' % station)
        facebook.current_user = facebook.user(identifier=station)
    return facebook


def init_dispatcher(shared: GlobalVariable) -> Dispatcher:
    facebook = SharedFacebook()
    dispatcher = Dispatcher()
    # create deliver delegates
    pusher = DefaultPusher(facebook=facebook)
    deliver = DefaultDeliver(database=shared.mdb, pusher=pusher)
    group_deliver = GroupDeliver(database=shared.mdb, facebook=facebook)
    broadcast_deliver = BroadcastDeliver()
    roamer = DefaultRoamer(database=shared.sdb, facebook=facebook)
    # set delegates and start
    dispatcher.database = shared.mdb
    dispatcher.facebook = facebook
    dispatcher.deliver = deliver
    dispatcher.group_deliver = group_deliver
    dispatcher.broadcast_deliver = broadcast_deliver
    dispatcher.roaming_deliver = roamer
    dispatcher.start()
    # start PushCenter
    center = PushCenter()
    center.start()
    return dispatcher


# noinspection PyUnusedLocal
def stop_dispatcher(shared: GlobalVariable) -> bool:
    dispatcher = Dispatcher()
    dispatcher.stop()
    # stop PushCenter
    center = PushCenter()
    center.stop()
    return True
