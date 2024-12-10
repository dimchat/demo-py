#! /usr/bin/env python3
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

import os
import sys
import getopt

from dimsdk import ID

path = os.path.abspath(__file__)
path = os.path.dirname(path)
path = os.path.dirname(path)
path = os.path.dirname(path)
sys.path.insert(0, path)

from dimples.utils import Log
from dimples.utils import Runner

from dimples.register.shared import GlobalVariable
from dimples.register.shared import show_help, generate, modify


#
# show logs
#
Log.LEVEL = Log.DEVELOP


DEFAULT_CONFIG = '/etc/dim/config.ini'


async def async_main():
    cmd = sys.argv[0]
    try:
        opts, args = getopt.getopt(args=sys.argv[1:],
                                   shortopts='hf:',
                                   longopts=['help', 'config='])
    except getopt.GetoptError:
        show_help(cmd=cmd, default_config=DEFAULT_CONFIG)
        sys.exit(1)
    # create global variable
    shared = GlobalVariable()
    await shared.prepare(default_config=DEFAULT_CONFIG)
    # check actions
    if len(args) == 1 and args[0] == 'generate':
        await generate(database=shared.adb)
    elif len(args) == 2 and args[0] == 'modify':
        identifier = ID.parse(identifier=args[1])
        assert identifier is not None, 'ID error: %s' % args[1]
        await modify(identifier=identifier, database=shared.adb)
    else:
        show_help(cmd=cmd, default_config=DEFAULT_CONFIG)


def main():
    Runner.sync_run(main=async_main())


if __name__ == '__main__':
    main()
