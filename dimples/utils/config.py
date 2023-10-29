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
from typing import Optional, Dict, List, Tuple

from dimsdk import Dictionary
from dimsdk import ID


class Node(Dictionary):
    """ DIM Network Node """

    def __init__(self, name: str = None, host: str = None, port: int = 0):
        super().__init__()
        if name is not None:
            self['name'] = name
        if host is not None:
            self['host'] = host
        if port > 0:
            self['port'] = port

    def __str__(self) -> str:
        clazz = self.__class__.__name__
        return '<%s host="%s" port=%d name="%s" />' % (clazz, self.host, self.port, self.name)

    def __repr__(self) -> str:
        clazz = self.__class__.__name__
        return '<%s host="%s" port=%d name="%s" />' % (clazz, self.host, self.port, self.name)

    @property
    def name(self) -> str:
        return self.get('name')

    @property
    def host(self) -> str:
        return self.get('host')

    @property
    def port(self) -> int:
        return self.get('port')


def get_socket_address(value: str) -> Tuple[str, int]:
    pair = value.split(':')
    if len(pair) == 2:
        return pair[0].strip(), int(pair[1])
    else:
        return pair[0].strip(), 9394


def parse_nodes(nodes: Dict[str, str]) -> List[Node]:
    """ parse lines with 'name = host:port, ID' format """
    stations = []
    for name in nodes:
        value = nodes[name]
        pair = value.split(',')
        host, port = get_socket_address(value=pair[0])
        node = Node(name=name, host=host, port=port)
        stations.append(node)
    return stations


def str_to_bool(value: Optional[str]) -> bool:
    if value is None or len(value) == 0:
        return False
    lower = value.lower()
    if lower not in ConfigParser.BOOLEAN_STATES:
        raise ValueError('Not a boolean: %s' % value)
    return ConfigParser.BOOLEAN_STATES[lower]


class Config(Dictionary):
    """ Config info from ini file """

    def get_identifier(self, section: str, option: str) -> Optional[ID]:
        sub = self.get(section)
        if sub is not None:
            return ID.parse(identifier=sub.get(option))

    def get_string(self, section: str, option: str) -> Optional[str]:
        sub = self.get(section)
        if sub is not None:
            return sub.get(option)

    def get_integer(self, section: str, option: str) -> int:
        sub = self.get(section)
        if sub is not None:
            val = sub.get(option)
            if val is not None:
                return int(val)
        return 0

    def get_boolean(self, section: str, option: str) -> bool:
        sub = self.get(section)
        if sub is not None:
            val = sub.get(option)
            return str_to_bool(value=val)

    def get_list(self, section: str, option: str, separator: str = ',') -> List[str]:
        """ get str and separate to a list """
        text = self.get_string(section=section, option=option)
        if text is None:
            return []
        result = []
        array = text.split(separator)
        for item in array:
            string = item.strip()
            if len(string) > 0:
                result.append(string)
        return result

    #
    #   database
    #

    @property
    def database_root(self) -> str:
        path = self.get_string(section='database', option='root')
        if path is None:
            return '/var/.dim'
        else:
            return path

    @property
    def database_public(self) -> str:
        path = self.get_string(section='database', option='public')
        if path is None:
            return '%s/public' % self.database_root   # /var/.dim/public
        else:
            return path

    @property
    def database_private(self) -> str:
        path = self.get_string(section='database', option='private')
        if path is None:
            return '%s/private' % self.database_root  # /var/.dim/private
        else:
            return path

    #
    #   station
    #

    @property
    def station_id(self) -> ID:
        return self.get_identifier(section='station', option='id')

    @property
    def station_host(self) -> str:
        ip = self.get_string(section='station', option='host')
        return '127.0.0.1' if ip is None else ip

    @property
    def station_port(self) -> int:
        num = self.get_integer(section='station', option='port')
        return num if num > 0 else 9394

    #
    #   ans
    #

    @property
    def ans_records(self) -> Optional[Dict[str, str]]:
        return self.get('ans')

    #
    #   neighbor stations
    #
    @property
    def neighbors(self) -> List[Node]:
        nodes = self.get('neighbors')
        if nodes is None:
            return []
        return parse_nodes(nodes=nodes)

    @classmethod
    def load(cls, file: str):
        info = load_ini(file=file)
        return cls(dictionary=info)


def load_ini(file: str) -> dict:
    parser = ConfigParser()
    parser.read(file)
    # parse all sections
    info = {}
    sections = parser.sections()
    for sec in sections:
        array = parser.items(section=sec)
        if array is None or len(array) == 0:
            # options empty
            continue
        lines = {}
        for item in array:
            name = item[0]
            value = item[1]
            lines[name] = value
        info[sec] = lines
    return info
