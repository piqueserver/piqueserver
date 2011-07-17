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

from pyspades.loaders import Loader
from pyspades.protocol import BaseConnection
from pyspades.tools import make_server_number, get_server_ip
from twisted.internet.protocol import DatagramProtocol
from pyspades.loaders import *
from pyspades.common import *
from twisted.internet import reactor
from twisted.internet.defer import Deferred

import random

HOST = 'ace-spades.com'
PORT = 32886

class AddServer(Loader):
    __slots__ = ['count', 'max_players', 'name']

    id = 4

    def read(self, reader):
        if reader.dataLeft() == 1:
            self.count = reader.readByte(True)
        else:
            self.max_players = reader.readByte(True)
            self.name = reader.readString()
    
    def write(self, reader):
        if self.count is None:
            reader.writeByte(self.max_players)
            reader.writeString(self.name)
        else:
            reader.writeByte(self.count, True)

add_server = AddServer()
connect_request = ConnectionRequest()

class MasterConnection(BaseConnection):
    disconnect_callback = None
    connected = False
    def __init__(self, protocol, name, max, defer):
        BaseConnection.__init__(self)

        self.protocol = protocol
    
        self.name = name
        self.max = max
        self.defer = defer
        self.auth_val = random.randint(0, 0xFFFF)
        self.send_request()
    
    def send_request(self):
        if self.connected:
            return
        connect_request.auth_val = self.auth_val
        connect_request.version = 0x11000000 # increments for each version
        connect_request.client = True
        self.send_loader(connect_request, False, 255)
        reactor.callLater(5, self.send_request)
    
    def loader_received(self, loader):
        if loader.id == ConnectionResponse.id:
            self.connection_id = loader.connection_id
            self.unique = loader.unique
            self.connected = True
            
            add_server.count = None
            add_server.name = self.name
            add_server.max_players = self.max
            self.send_contained(add_server)
            
            if self.defer is not None:
                self.defer.callback(self)
                self.defer = None
    
    def set_count(self, value):
        add_server.count = value
        self.send_contained(add_server)
    
    def disconnect(self):
        BaseConnection.disconnect(self)
        callback = self.disconnect_callback
        if callback is not None:
            callback()
        self.disconnect_callback = None
        self.protocol.transport.stopListening()
    
    def send_data(self, data):
        self.protocol.transport.write(data)

from twisted.web.client import getPage

def get_external_ip():
    return getPage(IP_GETTER)

class MasterProtocol(DatagramProtocol):
    connection_class = MasterConnection
    def __init__(self, name, max, defer = None):
        self.name = name
        self.max = max
        self.defer = defer
        
    def startProtocol(self):
        reactor.resolve(HOST).addCallback(self.hostResolved)
    
    def hostResolved(self, ip):
        self.transport.connect(ip, PORT)
        self.connection = self.connection_class(self, self.name, 
            self.max, self.defer)
        
    def set_count(self, value):
        self.connection.set_count(value)
        
    def datagramReceived(self, data, address):
        self.connection.data_received(data)

def get_master_connection(name, max, interface = ''):
    defer = Deferred()
    reactor.listenUDP(0, MasterProtocol(name, max, defer), 
        interface = interface)
    return defer