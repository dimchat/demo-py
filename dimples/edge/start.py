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

from dimples.utils import Log

from dimples.edge.shared import create_config, create_database, create_facebook
from dimples.edge.shared import GlobalVariable
from dimples.edge.octopus import Octopus


#
# show logs
#
Log.LEVEL = Log.DEVELOP


DEFAULT_CONFIG = '/etc/dim/edge.ini'


def main():
    # create global variable
    shared = GlobalVariable()
    # Step 1: load config
    config = create_config(app_name='DIM Network Edge', default_config=DEFAULT_CONFIG)
    shared.config = config
    # Step 2: create database
    adb, mdb, sdb = create_database(config=config)
    shared.adb = adb
    shared.mdb = mdb
    shared.sdb = sdb
    # Step 3: create facebook
    facebook = create_facebook(config=config, database=adb)
    shared.facebook = facebook
    # create & start octopus
    host = config.station_host
    port = config.station_port
    octopus = Octopus(shared=shared, local_host=host, local_port=port)
    octopus.start()


if __name__ == '__main__':
    main()
