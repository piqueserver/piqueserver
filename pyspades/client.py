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

"""
Client implementation - WIP
"""

from twisted.internet.protocol import DatagramProtocol
from twisted.internet import reactor
from pyspades.protocol import BaseConnection
from pyspades.bytereader import ByteReader
from pyspades.packet import Packet, load_server_packet
from pyspades.loaders import *
from pyspades.common import *
from pyspades import clientloaders, serverloaders
from pyspades.multidict import MultikeyDict

import random

class OtherClient(object):
    def __init__(self, protocol, name, player_id):
        self.name = name
        self.protocol = protocol
        self.player_id = player_id

class ClientConnection(BaseConnection):
    protocol = None
    def __init__(self, protocol):
        BaseConnection.__init__(self)
        self.protocol = protocol
        self.auth_val = random.randint(0, 0xFFFF)
        self.map = ByteReader()
        self.connections = MultikeyDict()
        
        connect_request = ConnectionRequest()
        connect_request.auth_val = self.auth_val
        connect_request.version = crc32(open('./data/client.exe', 'rb').read())
        self.send_loader(connect_request, False, 255)
    
    def send_join(self):
        loader = SizedData()
        data = ByteReader()
        join = clientloaders.JoinTeam()
        join.team = 1
        join.name = 'flotothelo'
        join.write(data)
        loader.data = data
        self.send_loader(loader, byte = 255)
    
    def loader_received(self, packet):
        # print 'got:', packet
        if packet.id == ConnectionResponse.id:
            self.connection_id = packet.connection_id
            self.unique = packet.unique
            self.connected = True
            print 'connected'
        elif hasattr(packet, 'data') and packet.id != MapData.id:
            print 'yay'
            if packet.id == SizedData.id and self.map is not None:
                print 'finished!'
                open('testy.vxl', 'wb').write(str(self.map))
                self.map = None
            data = packet.data
            contained = load_server_packet(data)
            if data.dataLeft():
                raw_input('not completely parsed')
            print contained, vars(contained)
            newdata = ByteReader()
            contained.write(newdata)
            if contained.id != serverloaders.PlayerData.id:
                if str(data) != str(newdata):
                    print hexify(data)
                    print hexify(newdata)
                    raw_input('incorrect save func')
        elif packet.id == MapData.id:
            data = packet.data
            if packet.num == 0:
                byte = data.readByte(True)
                if byte != 15:
                    raw_input()
            self.map.write(data.read())
        elif packet.id == Ack.id:
            pass
        elif packet.id == Packet10.id:
            print 'received packet10'
        elif packet.id == Ping.id:
            print 'received ping'
        else:
            print 'received:', packet
            raw_input('unknown packet')
    
    def send_data(self, data):
        self.protocol.transport.write(data)

class ClientProtocol(DatagramProtocol):    
    def __init__(self, host, port):
        self.host, self.port = host, port
    
    def startProtocol(self):
        self.transport.connect(self.host, self.port)
        self.connection = ClientConnection(self)
    
    def datagramReceived(self, data, address):
        self.connection.data_received(data)