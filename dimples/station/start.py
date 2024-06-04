#! /usr/bin/env python3
# -*- coding: utf-8 -*-
#
#   DIMS : DIM Station
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
from socketserver import ThreadingTCPServer

path = os.path.abspath(__file__)
path = os.path.dirname(path)
path = os.path.dirname(path)
path = os.path.dirname(path)
sys.path.insert(0, path)

from dimples.utils import Log, Runner

from dimples.station.shared import GlobalVariable
from dimples.station.shared import create_config, create_database, create_facebook
from dimples.station.shared import create_dispatcher
from dimples.station.shared import create_ans
from dimples.station.handler import RequestHandler


#
# show logs
#
Log.LEVEL = Log.DEVELOP


DEFAULT_CONFIG = '/etc/dim/station.ini'


async def async_main():
    # create global variable
    shared = GlobalVariable()
    # Step 1: load config
    config = await create_config(app_name='DIM Network Station', default_config=DEFAULT_CONFIG)
    shared.config = config
    # Step 2: create database
    adb, mdb, sdb = await create_database(config=config)
    shared.adb = adb
    shared.mdb = mdb
    shared.sdb = sdb
    # Step 3: create facebook
    sid = config.station_id
    assert sid is not None, 'current station ID not set: %s' % config
    facebook = await create_facebook(database=adb, current_user=sid)
    shared.facebook = facebook
    # Step 4: create dispatcher
    create_dispatcher(shared=shared)
    # Step 5: create ANS
    create_ans(config=config)
    # check bind host & port
    host = config.station_host
    port = config.station_port
    assert host is not None and port > 0, 'station config error: %s' % config
    server_address = (host, port)

    # start TCP server
    try:
        # ThreadingTCPServer.allow_reuse_address = True
        server = ThreadingTCPServer(server_address=server_address,
                                    RequestHandlerClass=RequestHandler,
                                    bind_and_activate=False)
        Log.info(msg='>>> TCP server %s starting...' % str(server_address))
        server.allow_reuse_address = True
        server.server_bind()
        server.server_activate()
        Log.info(msg='>>> TCP server %s is listening...' % str(server_address))
        server.serve_forever()
    except KeyboardInterrupt as ex:
        Log.info(msg='~~~~~~~~ %s' % ex)
    finally:
        Log.info(msg='======== station shutdown!')


def main():
    Runner.sync_run(main=async_main())


if __name__ == '__main__':
    main()
