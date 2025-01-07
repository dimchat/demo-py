# -*- coding: utf-8 -*-
#
#   Ming-Ke-Ming : Decentralized User Identity Authentication
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

from dimsdk import ReliableMessage
from dimsdk import FileContent
from dimsdk import Command, MetaCommand, DocumentCommand
from dimsdk import ReceiptCommand

from ..protocol import ReportCommand

from ..protocol import MetaType


#
#  Compatible with old versions
#
class Compatible:

    @classmethod
    def fix_meta_attachment(cls, msg: ReliableMessage):
        return _fix_meta_attachment(msg=msg)

    @classmethod
    def fix_meta_version(cls, meta: dict):
        return _fix_meta_version(meta=meta)

    @classmethod
    def fix_file_content(cls, content: FileContent):
        return _fix_file_content(content=content)

    @classmethod
    def fix_command(cls, content: Command) -> Command:
        return _fix_command(content=content)


def _fix_meta_attachment(msg: ReliableMessage):
    meta = msg.get('meta')
    if meta is not None:
        return _fix_meta_version(meta=meta)


def _fix_meta_version(meta: dict):
    version = meta.get('type')
    if version is None:
        version = meta.get('version')  # compatible with MKM 0.9.*
    elif isinstance(version, str) and 'algorithm' not in meta:
        # TODO: check number
        if len(version) > 2:
            meta['algorithm'] = version
    # compatible with v1.0
    version = MetaType.parse_int(version=version, default=0)
    if version > 0:
        meta['type'] = version
        meta['version'] = version
    return meta


def _fix_file_content(content: FileContent):
    pwd = content.get('key')
    if pwd is not None:
        # Tarsier version > 1.3.7
        # DIM SDK version > 1.1.0
        content['password'] = pwd
    else:
        # Tarsier version <= 1.3.7
        # DIM SDK version <= 1.1.0
        pwd = content.get('password')
        if pwd is not None:
            content['key'] = pwd
    return content


def _fix_command(content: Command) -> Command:
    # 1. fix 'cmd'
    content = _fix_cmd(content=content)
    # 2. fix other commands
    if isinstance(content, ReceiptCommand):
        # receipt
        _fix_receipt_command(content=content)
    elif isinstance(content, ReportCommand):
        # report
        _fix_report_command(content=content)
    elif isinstance(content, DocumentCommand):
        # document
        _fix_document_command(content=content)
    elif isinstance(content, MetaCommand):
        # meta
        meta = content.get('meta')
        if meta is not None:
            _fix_meta_version(meta=meta)
    # OK
    return content


def _fix_cmd(content: Command):
    cmd = content.get('cmd')
    if cmd is None:
        cmd = content.get('command')
        content['cmd'] = cmd
    elif 'command' not in content:
        content['command'] = cmd
        content = Command.parse(content=content.dictionary)
    return content


def _copy_receipt_values(content: ReceiptCommand, env: dict):
    for key in ['sender', 'receiver', 'sn', 'signature']:
        value = env.get(key)
        if value is not None:
            content[key] = value


# TODO: remove after all server/client upgraded
def _fix_receipt_command(content: ReceiptCommand):
    origin = content.get('origin')
    if origin is not None:
        # (v2.0)
        # compatible with v1.0
        content['envelope'] = origin
        # compatible with older version
        _copy_receipt_values(content=content, env=origin)
        return content
    # check for old version
    env = content.get('envelope')
    if env is not None:
        # (v1.0)
        # compatible with v2.0
        content['origin'] = env
        # compatible with older version
        _copy_receipt_values(content=content, env=env)
        return content
    # check for older version
    if 'sender' in content:  # and 'receiver' in content:
        # older version
        env = {
            'sender': content.get('sender'),
            'receiver': content.get('receiver'),
            'time': content.get('time'),
            'sn': content.get('sn'),
            'signature': content.get('signature'),
        }
        content['origin'] = env
        content['envelope'] = env
        return content


# TODO: remove after all server/client upgraded
def _fix_document_command(content: DocumentCommand):
    info = content.get('document')
    if info is not None:
        # (v2.0)
        #    "ID"      : "{ID}",
        #    "document" : {
        #        "ID"        : "{ID}",
        #        "data"      : "{JsON}",
        #        "signature" : "{BASE64}"
        #    }
        return content
    info = content.get('profile')
    if info is None:
        # query document command
        return content
    # 1.* => 2.0
    content.pop('profile')
    if isinstance(info, str):
        # compatible with v1.0
        #    "ID"        : "{ID}",
        #    "profile"   : "{JsON}",
        #    "signature" : "{BASE64}"
        content['document'] = {
            'ID': str(content.identifier),
            'data': info,
            'signature': content.get("signature")
        }
    else:
        # compatible with v1.1
        #    "ID"      : "{ID}",
        #    "profile" : {
        #        "ID"        : "{ID}",
        #        "data"      : "{JsON}",
        #        "signature" : "{BASE64}"
        #    }
        content['document'] = info
    return content


def _fix_report_command(content: ReportCommand):
    # check state for oldest version
    state = content.get('state')
    if state == 'background':
        # oldest version
        content['title'] = ReportCommand.OFFLINE
        return content
    elif state == 'foreground':
        # oldest version
        content['title'] = ReportCommand.ONLINE
        return content
    # check title for v1.0
    title = content.title
    if title is None:
        name = content.cmd
        if name != ReportCommand.REPORT:
            # (v1.0)
            # content: {
            #     'command': 'online', // or 'offline', 'apns', ...
            # }
            content['title'] = name
