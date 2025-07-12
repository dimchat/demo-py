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

from typing import Any, List, Dict

from dimsdk import Converter
from dimsdk import Document, DocumentUtils
from dimsdk import ContentType
from dimsdk import Content, FileContent, NameCard
from dimsdk import Command, MetaCommand, DocumentCommand
from dimsdk import ReceiptCommand
from dimsdk import ReliableMessage

from ..protocol import LoginCommand
from ..protocol import ReportCommand

from ..protocol import MetaVersion


"""
    Compatible with old versions
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~
"""


# TODO: remove after all server/client upgraded
class Compatible:

    @classmethod
    def fix_meta_attachment(cls, msg: ReliableMessage):
        meta = msg.get('meta')
        if meta is not None:
            _fix_meta_version(meta=meta)

    @classmethod
    def fix_meta_version(cls, meta: Dict[str, Any]):
        _fix_meta_version(meta=meta)

    @classmethod
    def fix_visa_attachment(cls, msg: ReliableMessage):
        visa = msg.get('visa')
        if visa is not None:
            _fix_doc_id(document=visa)

    @classmethod
    def fix_document_id(cls, document: Dict[str, Any]):
        _fix_doc_id(document=document)


def _fix_cmd(content: Dict[str, Any]):
    cmd = content.get('command')
    if cmd is None:
        # 'command' not exists, copy the value from 'cmd'
        cmd = content.get('cmd')
        if cmd is not None:
            content['command'] = cmd
        else:
            assert False, 'command error: %s' % content
    elif 'cmd' in content:
        # these two values must be equal
        assert content.get('cmd') == cmd, 'command error: %s' % content
    else:
        # copy value from 'command' to 'cmd'
        content['cmd'] = cmd


def _fix_did(content: Dict[str, Any]):
    did = content.get('did')
    if did is None:
        # 'did' not exists, copy the value from 'ID'
        did = content.get('ID')
        if did is not None:
            content['did'] = did
        # else:
        #     assert False, 'did not exists: %s' % content
    elif 'ID' in content:
        # these two values must be equal
        assert content.get('ID') == did, 'did error: %s' % content
    else:
        # copy value from 'did' to 'ID'
        content['ID'] = did


def _fix_doc_id(document: Dict[str, Any]):
    # 'ID' <-> 'did'
    _fix_did(document)
    return document


def _fix_meta_version(meta: Dict[str, Any]):
    version = meta.get('type')
    if version is None:
        version = meta.get('version')  # compatible with MKM 0.9.*
    elif isinstance(version, str) and 'algorithm' not in meta:
        # TODO: check number
        if len(version) > 2:
            meta['algorithm'] = version
    # compatible with v1.0
    version = MetaVersion.parse_int(version=version, default=0)
    if version > 0:
        meta['type'] = version
        meta['version'] = version


def _fix_file_content(content: Dict[str, Any]):
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


_file_types = [
    ContentType.FILE, 'file',
    ContentType.IMAGE, 'image',
    ContentType.AUDIO, 'audio',
    ContentType.VIDEO, 'video',
]


# TODO: remove after all server/client upgraded
class CompatibleIncoming:

    @classmethod
    def fix_content(cls, content: Dict[str, Any]):
        # get content type
        msg_type = content.get('type')
        msg_type = Converter.get_str(value=msg_type, default='')

        if msg_type in _file_types:
            # 1. 'key' <-> 'password'
            _fix_file_content(content=content)
            return

        if msg_type == ContentType.NAME_CARD or msg_type == 'card':
            # 1. 'ID' <-> 'did'
            _fix_did(content=content)
            return

        if msg_type == ContentType.COMMAND or msg_type == 'command':
            # 1. 'cmd' <-> 'command'
            _fix_cmd(content=content)
        #
        #  get command name
        #
        cmd = content.get('command')
        # cmd = Converter.get_str(value=cmd)
        if cmd is None or len(cmd) == 0:
            return

        # if cmd == Command.RECEIPT:
        #     pass

        if cmd == LoginCommand.LOGIN:
            # 2. 'ID' <-> 'did'
            _fix_did(content=content)
            return

        if cmd == Command.DOCUMENTS or cmd == 'document':
            # 2. cmd: 'document' -> 'documents'
            cls._fix_docs(content=content)

        if cmd == Command.META or cmd == Command.DOCUMENTS or cmd == 'document':
            # 3. 'ID' <-> 'did'
            _fix_did(content=content)
            meta = content.get('meta')
            if meta is not None:
                # 4. 'type' <-> 'version'
                _fix_meta_version(meta=meta)

    @classmethod
    def _fix_docs(cls, content: Dict[str, Any]):
        # cmd: 'document' -> 'documents'
        cmd = content.get('command')
        if cmd == 'document':
            content['command'] = 'documents'
        # 'document' -> 'documents'
        doc = content.get('document')
        if doc is not None:
            content['documents'] = [_fix_doc_id(document=doc)]
            content.pop('document', None)


# TODO: remove after all server/client upgraded
class CompatibleOutgoing:

    @classmethod
    def fix_content(cls, content: Content):
        # 0. change 'type' value from string to int
        cls._fix_type(content=content.dictionary)

        if isinstance(content, FileContent):
            # 1. 'key' <-> 'password'
            _fix_file_content(content=content.dictionary)
            return

        if isinstance(content, NameCard):
            # 1. 'ID' <-> 'did'
            _fix_did(content=content.dictionary)
            return

        if isinstance(content, Command):
            # 1. 'cmd' <-> 'command'
            _fix_cmd(content=content.dictionary)

        if isinstance(content, ReceiptCommand):
            # 2. check for v2.0
            _fix_receipt_command(content=content)
            return

        if isinstance(content, LoginCommand):
            # 2. 'ID' <-> 'did'
            _fix_did(content=content.dictionary)
            # 3. fix station
            station = content.get('station')
            if isinstance(station, Dict):
                _fix_did(station)
            # 4. fix provider
            provider = content.get('provider')
            if isinstance(provider, Dict):
                _fix_did(provider)
            return

        if isinstance(content, ReportCommand):
            _fix_report_command(content=content)
            return

        if isinstance(content, DocumentCommand):
            # 2. 'profile' -> 'document'
            _fix_document_command(content=content)
            # 3. cmd: 'documents' -> 'document
            cls._fix_docs(content=content)
        if isinstance(content, MetaCommand):
            # 4. 'ID' <-> 'did'
            _fix_did(content=content.dictionary)
            meta = content.get('meta')
            if meta is not None:
                # 5. 'type' <-> 'version'
                _fix_meta_version(meta=meta)

    @classmethod
    def _fix_type(cls, content: Dict[str, Any]):
        msg_type = content.get('type')
        if isinstance(msg_type, str):
            num_type = Converter.get_int(value=msg_type)
            if num_type is not None and num_type >= 0:
                content['type'] = num_type

    @classmethod
    def _fix_docs(cls, content: DocumentCommand):
        # cmd: 'documents' -> 'document'
        cmd = content.cmd
        if cmd == 'documents':
            content['cmd'] = 'document'
            content['command'] = 'document'
        # 'documents' -> 'document'
        array = content.get('documents')
        if isinstance(array, List):
            docs = Document.convert(array=array)
            last = DocumentUtils.last_document(documents=docs)
            if last is not None:
                content['document'] = _fix_doc_id(document=last.dictionary)
            if len(docs) == 1:
                content.pop('documents', None)
        doc = content.get('document')
        if isinstance(doc, Dict):
            _fix_doc_id(document=doc)


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
