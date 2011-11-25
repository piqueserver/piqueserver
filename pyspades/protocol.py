# Copyright (c) Mathias Kaerlev 2011.

# This file is part of pyspades.

# pyspades is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

# pyspades is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with pyspades.  If not, see <http://www.gnu.org/licenses/>.

from twisted.internet import reactor
from pyspades.bytes import ByteReader, ByteWriter
from pyspades.packet import Packet, generate_loader_data
from pyspades.loaders import Ack
from twisted.internet.defer import Deferred
from pyspades.loaders import *
from twisted.internet.task import LoopingCall
from pyspades.common import hexify, stringify, binify
import enet

import math

class BaseConnection(object):
    disconnected = False
    def __init__(self, protocol, peer):
        self.protocol = protocol
        self.peer = peer
    
    def disconnect(self):
        if self.disconnected:
            return
        self.disconnected = True
        self.peer.reset()
    
    def loader_received(self, loader):
        raise NotImplementedError('loader_received() not implemented')
    
    def send_contained(self, contained, sequence = False):
        if self.disconnected:
            return
        if sequence:
            flags = enet.PACKET_FLAG_UNSEQUENCED
        else:
            flags = enet.PACKET_FLAG_RELIABLE
        data = ByteWriter()
        contained.write(data)
        packet = enet.Packet(str(data), flags)
        self.peer.send(0, packet)
    
    # events
    def timer_received(self, value):
        # XXX we'll have to hack a bit on ENet to make it pass this
        # information to us
        pass
    
    def on_disconnect(self):
        pass

class BaseProtocol(object):
    connection_class = BaseConnection
    def __init__(self, port = None, interface = 'localhost', 
                 update_interval = 1 / 60.0):
        if port is not None and interface is not None:
            address = enet.Address(interface, port)
        else:
            address = None
        self.host = enet.Host(address, 32, 1)
        self.host.compress_with_range_coder()
        self.update_loop = LoopingCall(self.update)
        self.update_loop.start(update_interval, False)
        self.connections = {}
        self.clients = {}
    
    def connect(self, connection_class, host, port, version, channel_count = 1):
        peer = self.host.connect(enet.Address(host, port), channel_count, 
            version)
        connection = connection_class(self, peer)
        self.clients[peer] = connection
        return connection
    
    def on_connect(self, peer):
        connection = self.connection_class(self, peer)
        self.connections[peer] = connection
        connection.on_connect()
    
    def on_disconnect(self, peer):
        connection = self.connections.pop(peer)
        connection.disconnected = True
        connection.on_disconnect()
    
    def data_received(self, peer, packet):
        connection = self.connections[peer]
        connection.loader_received(packet)
    
    def update(self):
        while 1:
            event = self.host.service(0)
            if event is None:
                break
            event_type = event.type
            peer = event.peer
            is_client = peer in self.clients
            if event_type == enet.EVENT_TYPE_DISCONNECT:
                print 'le disconnect from', peer
            if is_client:
                connection = self.clients[peer]
                if event_type == enet.EVENT_TYPE_CONNECT:
                    connection.on_connect()
                elif event_type == enet.EVENT_TYPE_DISCONNECT:
                    connection.on_disconnect()
                    del self.clients[peer]
                elif event.type == enet.EVENT_TYPE_RECEIVE:
                    connection.loader_received(event.packet)
            else:
                if event_type == enet.EVENT_TYPE_CONNECT:
                    self.on_connect(peer)
                elif event_type == enet.EVENT_TYPE_DISCONNECT:
                    self.on_disconnect(peer)
                elif event.type == enet.EVENT_TYPE_RECEIVE:
                    self.data_received(peer, event.packet)
        