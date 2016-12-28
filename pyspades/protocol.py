# Copyright (c) Mathias Kaerlev 2011-2012.

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
from twisted.internet.defer import Deferred
from twisted.internet.task import LoopingCall
from pyspades.common import hexify, stringify, binify
import enet

import math

class BaseConnection(object):
    disconnected = False
    timeout_call = None
    def __init__(self, protocol, peer):
        self.protocol = protocol
        self.peer = peer
    
    def timed_out(self):
        self.disconnect()
    
    def disconnect(self, data = 0):
        if self.disconnected:
            return
        self.disconnected = True
        self.peer.disconnect(data);
        self.protocol.remove_peer(self.peer)
        self.on_disconnect()
    
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

    def on_connect(self):
        pass
    
    def on_disconnect(self):
        pass
    
    # properties
        
    @property
    def latency(self):
        return self.peer.roundTripTime

class BaseProtocol(object):
    connection_class = BaseConnection
    max_connections = 33
    is_client = False
    
    def __init__(self, port = None, interface = 'localhost', 
                 update_interval = 1 / 60.0):
        if port is not None and interface is not None:
            address = enet.Address(interface, port)
        else:
            address = None
        self.host = enet.Host(address, self.max_connections, 1)
        self.host.compress_with_range_coder()
        self.update_loop = LoopingCall(self.update)
        self.update_loop.start(update_interval, False)
        self.connections = {}
        self.clients = {}
    
    def connect(self, connection_class, host, port, version, channel_count = 1,
                timeout = 5.0):
        peer = self.host.connect(enet.Address(host, port), channel_count, 
            version)
        connection = connection_class(self, peer)
        connection.timeout_call = reactor.callLater(timeout, 
            connection.timed_out)
        self.clients[peer] = connection
        return connection
    
    def on_connect(self, peer):
        connection = self.connection_class(self, peer)
        self.connections[peer] = connection
        connection.on_connect()
    
    def on_disconnect(self, peer):
        try:
            connection = self.connections.pop(peer)
            connection.disconnected = True
            connection.on_disconnect()
        except KeyError:
            return
    
    def data_received(self, peer, packet):
        connection = self.connections[peer]
        connection.loader_received(packet)

    def remove_peer(self, peer):
        if peer in self.connections:
            del self.connections[peer]
        elif peer in self.clients:
            del self.clients[peer]
            self.check_client()

    def check_client(self):
        if self.is_client and not self.clients:
            self.update_loop.stop()
            self.update_loop = None
            self.host = None # important for GC
    
    def update(self):
        try:
            while 1:
                if self.host is None:
                    return
                try:
                    event = self.host.service(0)
                except IOError:
                    break
                if event is None:
                    break
                event_type = event.type
                if event_type == enet.EVENT_TYPE_NONE:
                    break
                peer = event.peer
                is_client = peer in self.clients
                if is_client:
                    connection = self.clients[peer]
                    if event_type == enet.EVENT_TYPE_CONNECT:
                        connection.on_connect()
                        connection.timeout_call.cancel()
                    elif event_type == enet.EVENT_TYPE_DISCONNECT:
                        connection.on_disconnect()
                        del self.clients[peer]
                        self.check_client()
                    elif event.type == enet.EVENT_TYPE_RECEIVE:
                        connection.loader_received(event.packet)
                else:
                    if event_type == enet.EVENT_TYPE_CONNECT:
                        self.on_connect(peer)
                    elif event_type == enet.EVENT_TYPE_DISCONNECT:
                        self.on_disconnect(peer)
                    elif event.type == enet.EVENT_TYPE_RECEIVE:
                        self.data_received(peer, event.packet)
        except:
            # make sure the LoopingCall doesn't catch this and stops
            import traceback
            traceback.print_exc()

def make_client(*arg, **kw):
    protocol = BaseProtocol()
    protocol.is_client = True
    return protocol.connect(*arg, **kw)