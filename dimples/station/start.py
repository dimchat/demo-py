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
import getopt

path = os.path.abspath(__file__)
path = os.path.dirname(path)
path = os.path.dirname(path)
path = os.path.dirname(path)
sys.path.insert(0, path)

from dimples.utils import Log
from dimples.database import Storage

from dimples.station.config import ConfigLoader, GlobalVariable
from dimples.station.config import init_database, init_facebook, init_dispatcher


#
# show logs
#
Log.LEVEL = Log.DEVELOP


def show_help():
    cmd = sys.argv[0]
    print('')
    print('    DIM Station')
    print('')
    print('usages:')
    print('    %s [--config=<FILE>]' % cmd)
    print('    %s [-h|--help]' % cmd)
    print('')
    print('optional arguments:')
    print('    --config        config file path (default: "/etc/dim/config.ini")')
    print('    --help, -h      show this help message and exit')
    print('')


def main():
    try:
        opts, args = getopt.getopt(args=sys.argv[1:],
                                   shortopts='hf:',
                                   longopts=['help', 'config='])
    except getopt.GetoptError:
        show_help()
        sys.exit(1)
    # check options
    config = None
    for opt, arg in opts:
        if opt == '--config':
            config = arg
        else:
            show_help()
            sys.exit(0)
    # check config filepath
    if config is None:
        config = '/etc/dim/config.ini'
    if not Storage.exists(path=config):
        show_help()
        print('')
        print('!!! config file not exists: %s' % config)
        print('')
        sys.exit(0)
    # load config
    config = ConfigLoader(file=config).load()
    # initializing
    shared = GlobalVariable(config=config)
    init_database(shared=shared)
    init_facebook(shared=shared)
    init_dispatcher(shared=shared)


if __name__ == '__main__':
    main()
