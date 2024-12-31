# -*- coding: utf-8 -*-
# ==============================================================================
# MIT License
#
# Copyright (c) 2021 Albert Moky
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
    Architecture Diagram
    ~~~~~~~~~~~~~~~~~~~~

        +--------------+
        |   Facebook   |
        +--------------+         PorterDelegate      ConnectionDelegate
              :  AccountDB      +--------------+        +----------+
              :                 |  GateKeeper  | . . . >|   Gate   |
        +--------------+        +--------------+        +----------+
        |   Messenger  | . . . >|   Session    |            Hub (Connection)
        +--------------+        +--------------+            Porter
                 MessageDB               SessionDB
                 Filter
                 Dispatcher
"""

from startrek import Hub, Channel
from startrek import Connection, ConnectionDelegate, ConnectionState
from startrek import BaseChannel
from startrek import BaseHub, BaseConnection, ActiveConnection

from startrek import Ship, Arrival, Departure, DeparturePriority
from startrek import Porter, PorterStatus, PorterDelegate, Gate
from startrek import ArrivalShip, ArrivalHall, DepartureShip, DepartureHall
from startrek import Dock, LockedDock, StarPorter, StarGate

from tcp import PlainArrival, PlainDeparture, PlainPorter
from tcp import StreamChannel, StreamHub
from tcp import ServerHub as TCPServerHub, ClientHub as TCPClientHub

from udp import PackageArrival, PackageDeparture, PackagePorter
from udp import PacketChannel, PacketHub
from udp import ServerHub as UDPServerHub, ClientHub as UDPClientHub

from .protocol import WebSocket, NetMsg, NetMsgHead, NetMsgSeq

from .ws import WSArrival, WSDeparture, WSPorter
from .mars import MarsStreamArrival, MarsStreamDeparture, MarsStreamPorter
from .mtp import MTPStreamArrival, MTPStreamDeparture, MTPStreamPorter
from .flexible import FlexiblePorter
from .gate import CommonGate, TCPServerGate, TCPClientGate, UDPServerGate, UDPClientGate
# from .gatekeeper import GateKeeper
from .queue import MessageWrapper, MessageQueue
from .session import BaseSession


__all__ = [

    #
    #   StarTrek
    #
    'Hub', 'Channel',
    'Connection', 'ConnectionDelegate', 'ConnectionState',
    'BaseChannel',
    'BaseHub', 'BaseConnection', 'ActiveConnection',

    'Ship', 'Arrival', 'Departure', 'DeparturePriority',
    'Porter', 'PorterStatus', 'PorterDelegate', 'Gate',
    'ArrivalShip', 'ArrivalHall', 'DepartureShip', 'DepartureHall',
    'Dock', 'LockedDock', 'StarPorter', 'StarGate',

    #
    #   TCP
    #
    'PlainArrival', 'PlainDeparture', 'PlainPorter',
    'StreamChannel', 'StreamHub', 'TCPServerHub', 'TCPClientHub',

    #
    #   UDP
    #
    'PackageArrival', 'PackageDeparture', 'PackagePorter',
    'PacketChannel', 'PacketHub', 'UDPServerHub', 'UDPClientHub',

    #
    #   Protocol
    #
    'WebSocket', 'NetMsg', 'NetMsgHead', 'NetMsgSeq',

    #
    #   Network
    #
    'WSArrival', 'WSDeparture', 'WSPorter',
    'MarsStreamArrival', 'MarsStreamDeparture', 'MarsStreamPorter',
    'MTPStreamArrival', 'MTPStreamDeparture', 'MTPStreamPorter',
    'FlexiblePorter',
    'CommonGate', 'TCPServerGate', 'TCPClientGate', 'UDPServerGate', 'UDPClientGate',
    # 'GateKeeper',
    'MessageWrapper', 'MessageQueue',
    'BaseSession',

]
