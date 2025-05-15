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
from typing import Optional, Any, Dict, List
from typing import Iterable

from aiou import JSONFile
from aiou import RedisConnector

from dimsdk import JSON
from dimsdk import Dictionary
from dimsdk import ID

from .log import Log, Logging
from .http import HttpClient


class MessageTransferAgent(Dictionary):
    """ DIM Network Node """

    # Override
    def __str__(self) -> str:
        clazz = self.__class__.__name__
        return '<%s host="%s" port=%d id="%s" />' % (clazz, self.host, self.port, self.identifier)

    # Override
    def __repr__(self) -> str:
        clazz = self.__class__.__name__
        return '<%s host="%s" port=%d id="%s" />' % (clazz, self.host, self.port, self.identifier)

    @property
    def identifier(self) -> Optional[ID]:
        string = self.get(key='ID')
        if string is None:
            string = self.get(key='id')
        return ID.parse(identifier=string)

    @property
    def host(self) -> str:
        return self.get(key='host', default='')

    @property
    def port(self) -> int:
        return self.get(key='port', default=0)

    @classmethod
    def parse(cls, node: Any):
        if node is None:
            return None
        elif isinstance(node, MessageTransferAgent):
            return node
        elif isinstance(node, Dictionary):
            node = node.dictionary
        host = node.get('host')
        port = node.get('port')
        if host is not None and port is not None and port > 0:
            return cls(dictionary=node)

    @classmethod
    def convert(cls, stations: Iterable[Any]):
        array = []
        for node in stations:
            item = cls.parse(node=node)
            if item is not None:
                array.append(item)
        return array

    @classmethod
    def revert(cls, stations: Iterable) -> List[Dict]:
        array = []
        for node in stations:
            assert isinstance(node, MessageTransferAgent), 'station node error: %s' % node
            array.append(node.dictionary)
        return array


# @Singleton
class Config(Logging):
    """ Config info from ini file """

    def __init__(self):
        super().__init__()
        self.__parser: Optional[ConfigParser] = None
        self.__info: Optional[Dict] = None
        self.__path: Optional[str] = None
        self.__redis: Optional[RedisConnector] = None
        self.__stations: List[MessageTransferAgent] = []

    async def load(self, path: str = None):
        if path is None:
            path = self.__path
            assert path is not None, 'config file path not set yet'
            self.info(msg='reloading config: %s' % path)
        else:
            self.__path = path
            self.info(msg='loading config: %s' % path)
        parser = ConfigParser()
        parser.read(path)
        self.__parser = parser
        self.__info = None
        self.__stations = None
        # load neighbor stations
        try:
            loader = NeighborLoader()
            self.__stations = await loader.load_stations(config=self)
        except Exception as error:
            self.error(msg='failed to load stations: %s, %s' % (error, parser))
        return self

    @property
    def dictionary(self) -> Optional[Dict]:
        info = self.__info
        if info is None:
            parser = self.__parser
            if parser is not None:
                info = _config_sections(parser=parser)
                self.__info = info
        return info

    # Override
    def __str__(self) -> str:
        return 'Config: %s' % self.dictionary

    # Override
    def __repr__(self) -> str:
        return 'Config: %s' % self.dictionary

    def get_section(self, section: str) -> Optional[Dict]:
        parser = self.__parser
        if parser is not None:
            return _section_options(parser=parser, section=section)

    def get_integer(self, section: str, option: str) -> int:
        parser = self.__parser
        if parser is None:
            return 0
        try:
            return parser.getint(section=section, option=option)
        except Exception as error:
            self.error(msg='failed to get integer: %s, %s, %s' % (section, option, error))
            return 0

    def get_boolean(self, section: str, option: str) -> bool:
        parser = self.__parser
        if parser is None:
            return False
        try:
            return parser.getboolean(section=section, option=option)
        except Exception as error:
            self.error(msg='failed to get boolean: %s, %s, %s' % (section, option, error))

    def get_string(self, section: str, option: str) -> Optional[str]:
        parser = self.__parser
        if parser is None:
            return None
        try:
            return parser.get(section=section, option=option)
        except Exception as error:
            self.error(msg='failed to get string : %s, %s, %s' % (section, option, error))

    def get_identifier(self, section: str, option: str) -> Optional[ID]:
        value = self.get_string(section=section, option=option)
        return ID.parse(identifier=value)

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
            return '%s/public' % self.database_root     # /var/.dim/public
        else:
            return path

    @property
    def database_protected(self) -> str:
        path = self.get_string(section='database', option='protected')
        if path is None:
            return '%s/protected' % self.database_root  # /var/.dim/protected
        else:
            return path

    @property
    def database_private(self) -> str:
        path = self.get_string(section='database', option='private')
        if path is None:
            return '%s/private' % self.database_root    # /var/.dim/private
        else:
            return path

    #
    #   memory cache
    #

    @property
    def redis_connector(self) -> Optional[RedisConnector]:
        redis_enable = self.get_boolean(section='redis', option='enable')
        if not redis_enable:
            self.warning(msg='redis disabled')
            return None
        redis = self.__redis
        if redis is None:
            # create redis connector
            host = self.get_string(section='redis', option='host')
            if host is None:
                host = 'localhost'
            port = self.get_integer(section='redis', option='port')
            if port is None or port <= 0:
                port = 6379
            username = self.get_string(section='redis', option='username')
            password = self.get_string(section='redis', option='password')
            self.info(msg='enable redis://%s:%s@%s:%d' % (username, password, host, port))
            redis = RedisConnector(host=host, port=port, username=username, password=password)
            self.__redis = redis
        return redis

    #
    #   station
    #

    @property
    def station_id(self) -> Optional[ID]:
        return self.get_identifier(section='station', option='id')

    @property
    def station_host(self) -> Optional[str]:
        return self.get_string(section='station', option='host')

    @property
    def station_port(self) -> Optional[int]:
        return self.get_integer(section='station', option='port')

    #
    #   ans
    #

    @property
    def ans_records(self) -> Optional[Dict[str, str]]:
        return self.get_section(section='ans')

    #
    #   neighbor stations
    #
    @property
    def neighbors(self) -> List[MessageTransferAgent]:
        all_stations = self.__stations
        if all_stations is None:
            return []
        else:
            host = self.station_host
            port = self.station_port
            sid = self.station_id
        # remove myself
        neighbor_stations = []
        for station in all_stations:
            if station.identifier == sid:
                continue
            elif station.port == port and station.host == host:
                continue
            neighbor_stations.append(station)
        return neighbor_stations


class NeighborLoader(Logging):

    def __init__(self):
        super().__init__()
        self.__http = HttpClient()

    async def load_stations(self, config: Config) -> Optional[List[MessageTransferAgent]]:
        # check remote URL
        source = config.get_string(section='neighbors', option='source')
        if source is None:
            stations = None
        else:
            stations = await self._download_stations(url=source)
        # check local path
        output = config.get_string(section='neighbors', option='output')
        if output is None:
            self.warning(msg='neighbors path not set')
        elif stations is None:
            stations = await self._load_stations(path=output)
        else:
            await self._save_stations(stations=stations, path=output)
        # OK
        return stations

    async def _download_stations(self, url: str) -> Optional[List[MessageTransferAgent]]:
        self.info(msg='downloading stations: %s' % url)
        http = self.__http
        try:
            text = http.cache_get(url=url)
            if text is None:
                return None
            else:
                stations = JSON.decode(string=text)
        except Exception as error:
            self.error(msg='failed to download stations: %s, %s' % (error, url))
            return None
        if isinstance(stations, Dict):
            stations = stations.get('stations')
        if isinstance(stations, List):
            return MessageTransferAgent.convert(stations=stations)

    async def _load_stations(self, path: str) -> Optional[List[MessageTransferAgent]]:
        self.info(msg='loading stations: %s' % path)
        try:
            stations = await JSONFile(path=path).read()
        except Exception as error:
            self.error(msg='failed to load stations: %s, %s' % (error, path))
            return None
        if isinstance(stations, Dict):
            stations = stations.get('stations')
        if isinstance(stations, List):
            return MessageTransferAgent.convert(stations=stations)

    async def _save_stations(self, stations: List[MessageTransferAgent], path: str) -> bool:
        info = MessageTransferAgent.revert(stations=stations)
        self.info(msg='saving %d station(s): %s' % (len(stations), path))
        try:
            return await JSONFile(path=path).write(info)
        except Exception as error:
            self.error(msg='failed to save stations: %s, %s' % (error, path))


def _config_sections(parser: ConfigParser) -> Dict:
    info = {}
    sections = parser.sections()
    for name in sections:
        options = _section_options(parser=parser, section=name)
        if options is None:
            options = {}
        info[name] = options
    return info


def _section_options(parser: ConfigParser, section: str) -> Optional[Dict]:
    try:
        array = parser.items(section=section)
    except Exception as error:
        Log.error(msg='failed to get section: %s, %s' % (section, error))
        return None
    # convert to dict
    options = {}
    for item in array:
        name = item[0]
        value = item[1]
        options[name] = value
    return options
