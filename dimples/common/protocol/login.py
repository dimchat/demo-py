# -*- coding: utf-8 -*-
#
#   DIMP : Decentralized Instant Messaging Protocol
#
#                                Written in 2019 by Moky <albert.moky@gmail.com>
#
# ==============================================================================
# MIT License
#
# Copyright (c) 2019 Albert Moky
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

"""
    Receipt Protocol
    ~~~~~~~~~~~~~~~~

    As receipt returned to sender to proofing the message's received
"""

from typing import Optional, Union, Any, Dict

from dimsdk import ID
from dimsdk import BaseCommand
from dimsdk import Station, ServiceProvider


class LoginCommand(BaseCommand):
    """
        Login Command
        ~~~~~~~~~~~~~~~

        data format: {
            type : 0x88,
            sn   : 123,

            cmd     : "login",
            time    : 0,
            //---- client info ----
            ID       : "{UserID}",
            device   : "{DeviceID}",  // (optional)
            agent    : "{UserAgent}", // (optional)
            //---- server info ----
            station  : {
                ID   : "{StationID}",
                host : "{IP}",
                port : {port}
            },
            provider : {
                ID   : "{SP_ID}"
            }
        }
    """
    LOGIN = 'login'

    def __init__(self, content: Dict[str, Any] = None, identifier: ID = None):
        if content is None:
            # create with ID
            super().__init__(cmd=self.LOGIN)
            assert identifier is not None, 'login ID should not empty'
            self['ID'] = str(identifier)
        else:
            # create with command content
            super().__init__(content=content)

    #
    #   Client Info
    #
    @property
    def identifier(self) -> ID:
        return ID.parse(identifier=self.get('ID'))

    # Device ID
    @property
    def device(self) -> Optional[str]:
        return self.get('device')

    @device.setter
    def device(self, value: str):
        if value is None:
            self.pop('device', None)
        else:
            self['device'] = value

    # User Agent
    @property
    def agent(self) -> Optional[str]:
        return self.get('agent')

    @agent.setter
    def agent(self, value: str):
        if value is None:
            self.pop('agent', None)
        else:
            self['agent'] = value

    #
    #   Server Info
    #
    @property
    def station(self) -> Optional[Dict]:
        return self.get('station')

    @station.setter
    def station(self, value: Union[Dict, Station]):
        if value is None:
            self.pop('station', None)
        elif isinstance(value, Dict):
            self['station'] = value
        else:
            assert isinstance(value, Station), 'station error: %s' % value
            self['station'] = {
                'ID': str(value.identifier),
                'host': value.host,
                'port': value.port,
            }

    @property
    def provider(self) -> Optional[Dict]:
        return self.get('provider')

    @provider.setter
    def provider(self, value: Union[Dict, ServiceProvider]):
        if value is None:
            self.pop('provider', None)
        elif isinstance(value, Dict):
            self['provider'] = value
        else:
            assert isinstance(value, ServiceProvider), 'SP error: %s' % value
            self['provider'] = {
                'ID': str(value.identifier),
            }
