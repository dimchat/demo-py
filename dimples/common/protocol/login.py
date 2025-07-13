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

from typing import Optional, Union, Dict

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

            command : "login",
            time    : 0,
            //---- client info ----
            did      : "{UserID}",
            device   : "{DeviceID}",  // (optional)
            agent    : "{UserAgent}", // (optional)
            //---- server info ----
            station  : {
                did  : "{StationID}",
                host : "{IP}",
                port : {port}
            },
            provider : {
                did  : "{SP_ID}"
            }
        }
    """
    LOGIN = 'login'

    def __init__(self, content: Dict = None, identifier: ID = None):
        if content is None:
            # 1. new command with ID
            assert identifier is not None, 'login ID should not empty'
            cmd = self.LOGIN
            super().__init__(cmd=cmd)
            self['did'] = str(identifier)
        else:
            # 2. command info from network
            assert identifier is None, 'params error: %s, %s' % (content, identifier)
            super().__init__(content)

    #
    #   Client Info
    #
    @property
    def identifier(self) -> ID:
        return ID.parse(identifier=self.get('did'))

    # Device ID
    @property
    def device(self) -> Optional[str]:
        return self.get_str(key='device')

    @device.setter
    def device(self, value: str):
        if value is None:
            self.pop('device', None)
        else:
            self['device'] = value

    # User Agent
    @property
    def agent(self) -> Optional[str]:
        return self.get_str(key='agent')

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
    def station(self, info: Union[Dict, Station]):
        if isinstance(info, Station):
            sid = info.identifier
            if sid.is_broadcast:
                self['station'] = {
                    'host': info.host,
                    'port': info.port,
                }
            else:
                self['station'] = {
                    'did': str(sid),
                    'host': info.host,
                    'port': info.port,
                }
        elif isinstance(info, Dict):
            self['station'] = info
        else:
            assert info is None, 'station info error: %s' % info
            self.pop('station', None)

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
                'did': str(value.identifier),
            }
