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
from pyspades.loaders import *
from pyspades.common import *
from twisted.internet import reactor
from twisted.internet.defer import Deferred
from pyspades.bytes import ByteReader

import random

MAX_SERVER_NAME_SIZE = 31

MASTER_VERSION = 29

HOST = 'ace-spades.com'
PORT = 32885

class AddServer(Loader):
    __slots__ = ['count', 'max_players', 'name', 'port']

    id = 4

    def read(self, reader):
        if reader.dataLeft() == 1:
            self.count = reader.readByte(True)
        else:
            self.max_players = reader.readByte(True)
            self.port = reader.readShort(True, False)
            self.name = reader.readString()
    
    def write(self, reader):
        if self.count is None:
            reader.writeByte(self.max_players)
            reader.writeShort(self.port, True, False)
            reader.writeString(self.name)
        else:
            reader.writeByte(self.count, True)

add_server = AddServer()

class MasterConnection(BaseConnection):
    disconnect_callback = None
    connected = False
    def on_connect(self):
        self.connected = True
            
        add_server.count = None
        add_server.name = self.name
        add_server.port = self.port
        add_server.max_players = self.max
        self.send_contained(add_server)
        
        if self.defer is not None:
            self.defer.callback(self)
            self.defer = None
    
    def set_count(self, value):
        add_server.count = value
        self.send_contained(add_server)
    
    def on_disconnect(self):
        callback = self.disconnect_callback
        if callback is not None:
            callback()
        self.disconnect_callback = None

from twisted.web.client import getPage

def get_external_ip():
    return getPage(IP_GETTER)

def get_master_connection(name, max, protocol):
    defer = Deferred()
    connection = protocol.connect(MasterConnection, HOST, PORT, MASTER_VERSION)
    connection.name = name
    connection.max = max
    connection.port = protocol.host.address.port
    connection.defer = defer
    return defer