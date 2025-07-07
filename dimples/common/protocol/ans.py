# -*- coding: utf-8 -*-
#
#   DIMP : Decentralized Instant Messaging Protocol
#
#                                Written in 2023 by Moky <albert.moky@gmail.com>
#
# ==============================================================================
# MIT License
#
# Copyright (c) 2023 Albert Moky
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
    ANS Protocol
    ~~~~~~~~~~~~

    Query/respond ANS records
"""

from typing import Union, Any, List, Dict

from dimsdk import Command, BaseCommand


class AnsCommand(BaseCommand):
    """
        ANS Command
        ~~~~~~~~~~~

        data format: {
            type : 0x88,
            sn   : 123,

            command : "ans",
            names   : "...",        // query with alias(es, separated by ' ')
            records : {             // respond with record(s)
                "{alias}": "{ID}",
            }
        }
    """

    ANS = 'ans'

    def __init__(self, content: Dict[str, Any] = None, names: str = None):
        if content is None:
            # 1. new command with names
            assert names is not None, 'ANS command error'
            cmd = AnsCommand.ANS
            super().__init__(cmd=cmd)
            self['names'] = names
        else:
            # 2. command info from network
            assert names is None, 'params error: %s, %s' % (content, names)
            super().__init__(content)

    #
    #   ANS aliases
    #
    @property
    def names(self) -> List[str]:
        string = self.get_str(key='names', default='')
        return string.split()

    @property
    def records(self) -> Dict[str, str]:
        dictionary = self.get('records')
        return {} if dictionary is None else dictionary

    @records.setter
    def records(self, value: Dict[str, str]):
        """ get map for (name => ID string) """
        self['records'] = value

    #
    #   Factories
    #

    @classmethod
    def query(cls, names: Union[str, List[str]]) -> Command:
        if isinstance(names, List):
            names = ' '.join(names)
        return cls(names=names)

    @classmethod
    def response(cls, names: Union[str, List[str]], records: Dict[str, str]) -> Command:
        if isinstance(names, List):
            names = ' '.join(names)
        command = cls(names=names)
        command.records = records
        return command
