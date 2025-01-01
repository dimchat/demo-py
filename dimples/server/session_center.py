# -*- coding: utf-8 -*-
#
#   DIM-SDK : Decentralized Instant Messaging Software Development Kit
#
#                                Written in 2019 by Moky <albert.moky@gmail.com>
#
# ==============================================================================
# MIT License
#
# Copyright (c) 2019 Albert Moky
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
    Session Server
    ~~~~~~~~~~~~~~

    for user connection
"""

import threading
import weakref
from typing import MutableMapping, MutableSet
from typing import Optional, Dict, Set, Tuple

from startrek.types import SocketAddress

from dimsdk import ID

from ..utils import Logging
from ..utils import Singleton
from ..common import Session


class SessionPool(Logging):

    def __init__(self):
        super().__init__()
        # ID => remote addresses
        self.__addresses: Dict[ID, MutableSet[Tuple[str, int]]] = {}
        # remote address => session
        self.__sessions: MutableMapping[SocketAddress, Session] = weakref.WeakValueDictionary()

    def all_addresses(self, identifier: ID) -> MutableSet[Tuple[str, int]]:
        addresses = self.__addresses.get(identifier)
        if addresses is None:
            addresses = set()
        elif len(addresses) == 0:
            # remote addresses empty, remote it from cache
            self.__addresses.pop(identifier, None)
        return addresses

    def add_address(self, identifier: ID, remote: SocketAddress):
        all_addresses = self.__addresses.get(identifier)
        if all_addresses is None:
            all_addresses = set()
            self.__addresses[identifier] = all_addresses
        all_addresses.add(remote)

    def remove_address(self, identifier: ID, remote: SocketAddress):
        all_addresses = self.__addresses.get(identifier)
        if all_addresses is not None:
            all_addresses.discard(remote)
            if len(all_addresses) == 0:
                self.__addresses.pop(identifier, None)

    def all_users(self) -> Set[ID]:
        return set(self.__addresses.keys())

    def get_session(self, remote: SocketAddress) -> Optional[Session]:
        return self.__sessions.get(remote)

    def add_session(self, session: Session):
        address = session.remote_address
        assert address is not None, 'session remote address error: %s' % session
        assert session.identifier is None, 'session ID error: %s' % session
        self.__sessions[address] = session

    def remove_session(self, remote: SocketAddress):
        self.__sessions.pop(remote, None)

    def all_sessions(self, identifier: ID) -> Set[Session]:
        all_addresses = self.__addresses.get(identifier)
        if all_addresses is None:
            return set()
        candidates = set()
        clone_addresses = set(all_addresses)  # copy
        for remote in clone_addresses:
            session = self.__sessions.get(remote)
            if session is None:
                self.warning(msg='session removed: %s, %s' % (identifier, remote))
                all_addresses.discard(remote)
                # self.remove_address(identifier=identifier, remote=remote)
                continue
            elif session.identifier != identifier:
                self.warning(msg='session reused: %s, %s, %s' % (identifier, remote, session))
                all_addresses.discard(remote)
                # self.remove_address(identifier=identifier, remote=remote)
                continue
            # got it
            candidates.add(session)
        if len(all_addresses) == 0:
            # remote addresses empty, remote it from cache
            self.__addresses.pop(identifier, None)
        return candidates


@Singleton
class SessionCenter:

    def __init__(self):
        super().__init__()
        self.__pool = SessionPool()
        self.__lock = threading.Lock()

    def all_users(self) -> Set[ID]:
        """ Get all users """
        with self.__lock:
            return self.__pool.all_users()

    # def get_session(self, remote: SocketAddress) -> Optional[Session]:
    #     """ Get session by remote address """
    #     with self.__lock:
    #         return self.__pool.get_session(remote=remote)

    def add_session(self, session: Session):
        """ Cache session with remote address """
        with self.__lock:
            remote = session.remote_address
            # check old session
            old = self.__pool.get_session(remote=remote)
            if old is not None:
                # remove old session with remote address
                self.__pool.remove_session(remote=remote)
                # remove remote address with ID if exists
                oid = session.identifier
                if oid is not None:
                    self.__pool.remove_address(identifier=oid, remote=remote)
            # add new session
            self.__pool.add_session(session=session)
        if old is not None:
            # set session inactive
            old.set_active(active=False)
        # assert session.identifier is None, 'new session error: %s' % session
        return True

    def remove_session(self, session: Session):
        """ Remove the session """
        identifier = session.identifier
        address = session.remote_address
        assert address is not None, 'session error: %s' % session
        with self.__lock:
            # remove session with remote address
            self.__pool.remove_session(remote=address)
            # remove remote address with ID if exists
            if identifier is not None:
                self.__pool.remove_address(identifier=identifier, remote=address)
        # set session inactive
        session.set_active(active=False)
        return True

    def update_session(self, session: Session, identifier: ID):
        """ Update ID in this session """
        oid = session.identifier
        if oid == identifier:
            # nothing changed
            return False
        address = session.remote_address
        assert address is not None, 'session error: %s' % session
        with self.__lock:
            if oid is not None:
                # remove remote address from old ID
                self.__pool.remove_address(identifier=oid, remote=address)
            # insert remote address for new ID
            self.__pool.add_address(identifier=identifier, remote=address)
        # update session ID
        session.set_identifier(identifier=identifier)
        return True

    def active_sessions(self, identifier: ID) -> Set[Session]:
        """ Get all active sessions with user ID """
        actives: Set[Session] = set()
        with self.__lock:
            all_sessions = self.__pool.all_sessions(identifier=identifier)
            for session in all_sessions:
                if session.active:
                    actives.add(session)
        return actives

    def is_active(self, identifier: ID) -> bool:
        """ check whether user online """
        with self.__lock:
            all_sessions = self.__pool.all_sessions(identifier=identifier)
            for session in all_sessions:
                if session.active:
                    # got one active
                    return True
