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

from mkm import ID

cur = os.path.abspath(__file__)
cur = os.path.dirname(cur)
cur = os.path.dirname(cur)
cur = os.path.dirname(cur)
sys.path.insert(0, cur)

from dimples.utils import Log
from dimples.database import AccountDatabase
from dimples.register.generate import generate
from dimples.register.modify import modify


#
# show logs
#
Log.LEVEL = Log.DEVELOP


def show_help():
    cmd = sys.argv[0]
    print('')
    print('    DIM account generate/modify')
    print('')
    print('usages:')
    print('    %s [--root=<DIR>] generate' % cmd)
    print('    %s [--root=<DIR>] modify <ID>' % cmd)
    print('    %s [-h|--help]' % cmd)
    print('')
    print('actions:')
    print('    generate        create new ID, meta & document')
    print('    modify <ID>     edit document with ID')
    print('')
    print('optional arguments:')
    print('    --help, -h      show this help message and exit')
    print('    --root          set root directory (default: "/var/.dim")')
    print('    --public        set directory for meta & document')
    print('    --private       set directory for private keys')
    print('')


def main():
    try:
        opts, args = getopt.getopt(args=sys.argv[1:],
                                   shortopts='hr:p:s:',
                                   longopts=['help', 'root=', 'public=', 'private='])
    except getopt.GetoptError:
        show_help()
        sys.exit(1)
    # check options
    root_dir = None
    pub_dir = None
    pri_dir = None
    for opt, arg in opts:
        if opt == '--root':
            root_dir = arg
        elif opt == '--private':
            pri_dir = arg
        elif opt == '--public':
            pub_dir = arg
        else:
            show_help()
            sys.exit(0)
    db = AccountDatabase(root=root_dir, public=pub_dir, private=pri_dir)
    # check actions
    if len(args) == 1 and args[0] == 'generate':
        generate(db=db)
    elif len(args) == 2 and args[0] == 'modify':
        identifier = ID.parse(identifier=args[1])
        assert identifier is not None, 'ID error: %s' % args[1]
        modify(identifier=identifier, db=db)
    else:
        show_help()


if __name__ == '__main__':
    main()
