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
Client implementation - NOT DONE YET AT ALL!
"""

from twisted.internet.protocol import DatagramProtocol
from pyspades.bytereader import ByteReader
from pyspades.packet import Packet
from pyspades.loaders import *

import random
import zlib
import time

def crc32(data):
    return zlib.crc32(data) & 0xffffffff

def timer():
    return int(time.time() * 1000)

class Timer(object):
    def __init__(self, offset = 0):
        self.offset = offset
        self.current = timer()
    
    def get_value(self):
        return (self.offset + timer() - self.current) & 0xFFFF

ack_packet = Ack()

class ClientProtocol(DatagramProtocol):
    connectionId = None
    unique = None
    connected = False
    authVal = None
    client_timer = server_timer = None
    
    def __init__(self, host, port):
        self.host, self.port = host, port
        self.in_packet = Packet()
        self.out_packet = Packet()
        self.authVal = random.randint(0, 0xFFFF)
        self.client_timer = Timer(0)
    
    def startProtocol(self):
        self.transport.connect(self.host, self.port)
        connect_request = ConnectionRequest()
        connect_request.auth_val = self.authVal
        connect_request.version = crc32(open('../client.exe', 'rb').read())
        connect_request.ack = True
        # connect_request.byte = -1
        # connect_request.sequence = 1
        self.sendLoader(connect_request, True)
        print 'yahay'
        
    def sendLoader(self, loader, timer = False):
        self.out_packet.packets = [loader]
        self.out_packet.unique = self.unique
        self.out_packet.connectionId = self.connectionId
        self.out_packet.timer = self.client_timer.get_value()
        data = self.out_packet.generate()
        self.transport.write(str(data))
    
    def write_packet(self, packet_id):
        pass
    
    def datagramReceived(self, data, (host, port)):
        reader = ByteReader(data)
        in_packet = self.in_packet
        in_packet.read(data, False)
        if in_packet.timer is not None and self.server_timer is None:
            self.server_timer = Timer(in_packet.timer)
        for packet in in_packet.packets:
            if packet.ack:
                print 'ack wanted:', in_packet.timer, packet.byte, packet.sequence
            if packet.id == ConnectionResponse.id:
                if self.connected:
                    continue
                # if packet.auth_val != self.authVal:
                    # print 'what?'
                self.connectionId = packet.connection_id
                self.unique = packet.unique
                self.connected = True
            if packet.ack:
                ack_packet.byte = packet.byte
                ack_packet.timer = in_packet.timer
                ack_packet.sequence2 = packet.sequence
                ack_packet.sequence = 1
                self.sendLoader(ack_packet, False)
        print 'received:', self.in_packet.packets