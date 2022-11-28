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
from typing import List, Tuple

from dimsdk import ID

from .utils import json_encode, json_decode


class Node:
    """ DIM Network Node """

    def __init__(self, name: str, host: str, port: int, identifier: ID):
        super().__init__()
        self.name = name
        self.host = host
        self.port = port
        self.identifier = identifier

    def __str__(self) -> str:
        return self.to_json()

    def __repr__(self) -> str:
        return self.to_json()

    def to_json(self) -> str:
        sid = self.identifier
        if sid is not None:
            sid = str(sid)
        info = {
            'ID': sid,
            'host': self.host,
            'port': self.port,
        }
        return json_encode(obj=info)


def get_socket_address(value: str) -> Tuple[str, int]:
    pair = value.split(':')
    if len(pair) == 2:
        return pair[0].strip(), int(pair[1])
    else:
        return pair[0].strip(), 9394


def parse_nodes(nodes: List[Tuple[str, str]]) -> List[Node]:
    """ parse lines with 'name = host:port, ID' format """
    stations = []
    for line in nodes:
        name = line[0]
        value = line[1]
        pair = value.split(',')
        host, port = get_socket_address(value=pair[0])
        sid = ID.parse(identifier=pair[1].strip())
        stations.append(Node(name=name, host=host, port=port, identifier=sid))
    return stations


class Config:

    def __init__(self, station: ID, host: str, port: int,
                 root: str, public: str, private: str,
                 neighbors: List[Node]):
        super().__init__()
        self.station = station
        # server
        self.host = host
        self.port = port
        # database
        self.root = root
        self.public = public
        self.private = private
        # network nodes
        self.neighbors = neighbors

    def __str__(self) -> str:
        return self.to_json()

    def __repr__(self) -> str:
        return self.to_json()

    def to_json(self) -> str:
        info = {
            'database': {
                'root': self.root,
                'public': self.public,
                'private': self.private,
            },
            'server': {
                'host': self.host,
                'port': self.port,
            },
            'ans': {
                'station': str(self.station),
            },
            'neighbors': json_decode(string=str(self.neighbors)),
        }
        return json_encode(obj=info)

    @classmethod
    def create(cls, station: ID = None, host: str = None, port: int = None,
               root: str = None, public: str = None, private: str = None,
               neighbors: List[Node] = None):
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
        # nodes
        if neighbors is None:
            neighbors = []
        # create
        return cls(station=station, host=host, port=port,
                   root=root, public=public, private=private,
                   neighbors=neighbors)


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

    def _get_options(self, section: str) -> List[Tuple[str, str]]:
        try:
            return self.__parser.items(section=section)
        except NoSectionError:
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
        # nodes
        neighbors = self._get_options(section='neighbors')
        #
        # 2. check options
        #
        if station is not None:
            station = ID.parse(identifier=station)
        if neighbors is not None:
            neighbors = parse_nodes(nodes=neighbors)
        #
        # 3. create config
        #
        return Config.create(station=station, host=host, port=port,
                             root=root, public=public, private=private,
                             neighbors=neighbors)
