# -*- coding: utf-8 -*-
#
#   DIME : DIM Edge
#
#                                Written in 2022 by Moky <albert.moky@gmail.com>
#
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

import os
import sys

path = os.path.abspath(__file__)
path = os.path.dirname(path)
path = os.path.dirname(path)
path = os.path.dirname(path)
sys.path.insert(0, path)

from dimples.utils import Log, Runner

from dimples.client import ClientFacebook
from dimples.client import ClientMessenger
from dimples.client import ClientSession
from dimples.client import Terminal

from dimples.edge.shared import GlobalVariable
from dimples.edge.shared import create_config
from dimples.edge.octopus import Octopus
from dimples.edge.messenger import InnerMessenger, OuterMessenger


class InnerClient(Terminal):

    # Override
    def _create_messenger(self, facebook: ClientFacebook, session: ClientSession) -> ClientMessenger:
        shared = GlobalVariable()
        messenger = InnerMessenger(session=session, facebook=facebook, database=shared.mdb)
        messenger.terminal = self  # Weak Reference
        shared.messenger = messenger
        return messenger


class OuterClient(Terminal):

    # Override
    def _create_messenger(self, facebook: ClientFacebook, session: ClientSession) -> ClientMessenger:
        shared = GlobalVariable()
        messenger = OuterMessenger(session=session, facebook=facebook, database=shared.mdb)
        messenger.terminal = self
        return messenger


class OctopusClient(Octopus):

    # Override
    async def create_inner_terminal(self, host: str, port: int) -> Terminal:
        shared = GlobalVariable()
        terminal = InnerClient(facebook=shared.facebook, database=shared.sdb)
        messenger = await terminal.connect(host=host, port=port)
        # set octopus
        assert isinstance(messenger, InnerMessenger)
        messenger.octopus = self
        # start an async task in background
        terminal.start()
        return terminal

    # Override
    async def create_outer_terminal(self, host: str, port: int) -> Terminal:
        shared = GlobalVariable()
        terminal = OuterClient(facebook=shared.facebook, database=shared.sdb)
        messenger = await terminal.connect(host=host, port=port)
        # set octopus
        assert isinstance(messenger, OuterMessenger)
        messenger.octopus = self
        # start an async task in background
        terminal.start()
        return terminal


#
# show logs
#
Log.LEVEL = Log.DEVELOP


DEFAULT_CONFIG = '/etc/dim/config.ini'


async def async_main():
    # create global variable
    shared = GlobalVariable()
    config = await create_config(app_name='DIM Network Edge', default_config=DEFAULT_CONFIG)
    await shared.prepare(config=config)
    #
    #  Login
    #
    sid = config.station_id
    await shared.login(current_user=sid)
    #
    #  Station host & port
    #
    host = config.station_host
    port = config.station_port
    assert host is not None and port > 0, 'station config error: %s' % config
    host = '127.0.0.1'
    #
    #  Start Octopus Client
    #
    octopus = OctopusClient(database=shared.sdb, local_host=host, local_port=port)
    await octopus.run()
    Log.warning(msg='octopus stopped: %s' % octopus)


def main():
    Runner.sync_run(main=async_main())


if __name__ == '__main__':
    main()
