# -*- coding: utf-8 -*-
#
#   DIM-SDK : Decentralized Instant Messaging Software Development Kit
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

import random
from typing import Optional

from dimsdk import PortableNetworkFile
from dimsdk import EncryptKey, SignKey
from dimsdk import AsymmetricKey, PrivateKey
from dimsdk import EntityType, ID
from dimsdk import MetaType, Meta
from dimsdk import Visa, BaseVisa
from dimsdk import Bulletin, BaseBulletin

from .dbi import AccountDBI, PrivateKeyDBI


class Register:

    def __init__(self, database: AccountDBI):
        super().__init__()
        self.__db = database

    @property
    def database(self) -> AccountDBI:
        return self.__db

    def create_user(self, name: str, avatar: Optional[PortableNetworkFile]) -> ID:
        """
        Generate user account

        :param name:   user name
        :param avatar: photo URL
        :return: user ID
        """
        #
        #   Step 1. generate private key (with asymmetric algorithm)
        #
        id_key = PrivateKey.generate(algorithm=AsymmetricKey.ECC)
        #
        #   Step 2: generate meta with private key (and meta seed)
        #
        meta = Meta.generate(version=MetaType.ETH, private_key=id_key)
        #
        #   Step 3: generate ID with meta
        #
        identifier = ID.generate(meta=meta, network=EntityType.USER)
        #
        #   Step 4: generate visa with ID and sign with private key
        #
        msg_key = PrivateKey.generate(algorithm=AsymmetricKey.RSA)
        visa_key = msg_key.public_key
        visa = self._create_visa(user=identifier, visa_key=visa_key, private_key=id_key, name=name, avatar=avatar)
        #
        #   Step 5: save private key, meta & visa in local storage
        #
        db = self.database
        db.save_private_key(key=id_key, user=identifier, key_type=PrivateKeyDBI.META)
        db.save_private_key(key=msg_key, user=identifier, key_type=PrivateKeyDBI.VISA)
        db.save_meta(meta=meta, identifier=identifier)
        db.save_document(document=visa)
        # OK
        return identifier

    def create_group(self, founder: ID, name: str, seed: str = None) -> ID:
        """
        Generate group account

        :param founder: group founder
        :param name:    group title
        :param seed:    ID.name
        :return: group ID
        """
        if seed is None or len(seed) == 0:
            r = random.randint(10000, 999999999)  # 10,000 ~ 999,999,999
            seed = 'Group-%d' % r
        db = self.database
        #
        #   Step 1: get private key of founder
        #
        private_key = db.private_key_for_visa_signature(user=founder)
        #
        #   Step 2: generate meta with private key (and meta seed)
        #
        meta = Meta.generate(version=MetaType.MKM, private_key=private_key, seed=seed)
        #
        #   Step 3: generate ID with meta
        #
        identifier = ID.generate(meta=meta, network=EntityType.GROUP)
        #
        #   Step 4: generate bulletin with ID and sign with founder's private key
        #
        doc = self._create_bulletin(group=identifier, private_key=private_key, name=name, founder=founder)
        #
        #   Step 5: save meta & bulletin in local storage
        #
        db.save_meta(meta=meta, identifier=identifier)
        db.save_document(document=doc)
        #
        #   Step 6: add founder as first member
        #
        members = [founder]
        db.save_members(members=members, group=identifier)
        # OK
        return identifier

    # noinspection PyMethodMayBeStatic
    def _create_visa(self, user: ID, visa_key: EncryptKey, private_key: SignKey,
                     name: str, avatar: Optional[PortableNetworkFile]) -> Visa:
        """ create user document """
        assert user.is_user, 'user ID error: %s' % user
        doc = BaseVisa(identifier=user)
        # App ID
        doc.set_property(key='app_id', value='chat.dim.tarsier')
        # nickname
        doc.name = name
        # avatar
        if avatar is not None:
            doc.avatar = avatar
        # public key
        doc.public_key = visa_key
        # sign it
        sig = doc.sign(private_key=private_key)
        assert sig is not None, 'failed to sign visa: %s' % user
        return doc

    # noinspection PyMethodMayBeStatic
    def _create_bulletin(self, group: ID, private_key: SignKey,
                         name: str, founder: ID) -> Bulletin:
        """ create group document """
        assert group.is_group, 'group ID error: %s' % group
        doc = BaseBulletin(identifier=group)
        # App ID
        doc.set_property(key='app_id', value='chat.dim.tarsier')
        # group founder
        doc.set_property(key='founder', value=str(founder))
        # group name
        doc.name = name
        # sign it
        sig = doc.sign(private_key=private_key)
        assert sig is not None, 'failed to sign bulletin: %s' % group
        return doc
