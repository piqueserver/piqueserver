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
from pyspades import clientloaders, serverloaders
from twisted.internet.defer import Deferred
from pyspades.multidict import MultikeyDict

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

class OtherClient(object):
    def __init__(self, protocol, name, player_id):
        self.name = name
        self.protocol = protocol
        self.player_id = player_id

class ClientProtocol(DatagramProtocol):
    connectionId = None
    unique = None
    connected = False
    auth_val = None
    client_timer = server_timer = None
    map = None
    sequence = 0
    server_sequence = 0
    packets = None
    packetDeferreds = None
    clients = None
    
    def __init__(self, host, port):
        self.host, self.port = host, port
        self.in_packet = Packet()
        self.out_packet = Packet()
        self.auth_val = random.randint(0, 0xFFFF)
        self.client_timer = Timer(0)
        self.packets = {}
        self.packet_deferreds = {}
        self.map = ByteReader()
        self.clients = MultikeyDict()
    
    def startProtocol(self):
        self.transport.connect(self.host, self.port)
        connect_request = ConnectionRequest()
        connect_request.auth_val = self.auth_val
        connect_request.version = crc32(open('../client.exe', 'rb').read())
        self.sendLoader(connect_request, True)
        
    def sendLoader(self, loader, ack = False):
        self.sequence += 1
        timer = self.client_timer.get_value()
        sequence = 1
        loader.sequence = sequence
        self.out_packet.packets = [loader]
        self.out_packet.unique = self.unique
        self.out_packet.connectionId = self.connectionId
        self.out_packet.timer = timer
        data = self.out_packet.generate()
        loader.ack = ack
        self.transport.write(str(data))
        if ack:
            defer = Deferred()
            self.packet_deferreds[(timer, sequence)] = defer
            return defer
    
    def sendJoin(self):
        loader = UserInput()
        data = ByteReader()
        join = clientloaders.JoinTeam()
        join.team = 1
        join.name = 'flotothelo'
        join.write(data)
        loader.data = data
        self.sendLoader(loader)
    
    def datagramReceived(self, data, (host, port)):
        reader = ByteReader(data)
        in_packet = self.in_packet
        in_packet.read(data, False)
        if in_packet.timer is not None and self.server_timer is None:
            self.server_timer = Timer(in_packet.timer)

        received = []
        for packet in in_packet.packets:
            if packet.ack:
                ack_packet.byte = packet.byte
                ack_packet.timer = in_packet.timer
                ack_packet.sequence2 = packet.sequence
                self.sendLoader(ack_packet, False)
            if packet.byte == 255:
                received.append(packet)
                continue
            if packet.sequence < self.server_sequence:
                continue
            self.packets[packet.sequence] = packet

        while 1:
            try:
                received.append(self.packets.pop(self.server_sequence + 1))
                self.server_sequence += 1
            except KeyError:
                break

        for packet in received:
            if packet.id == ConnectionResponse.id:
                if self.connected:
                    continue
                self.connectionId = packet.connection_id
                self.unique = packet.unique
                self.connected = True
            elif hasattr(packet, 'data') and packet.id != MapData.id:
                if packet.id == UserInput.id and self.map is not None:
                    print 'finished!'
                    open('testy.vxl', 'wb').write(str(self.map))
                    self.map = None
                data = packet.data
                firstByte = ord(str(data)[0])
                type = firstByte & 0xF
                print hexify(str(data)), '%r' % str(data), self.in_packet.connectionId
                # missing packets: 0, 1
                # implemented packets: 2, 3, 5, 6, 7, 8, 9, 10, 11, 12, 13

                else:
                    raw_input('unknown type')
                if data.dataLeft():
                    raw_input('not completely parsed')
            elif packet.id == MapData.id:
                data = packet.data
                if packet.num == 0:
                    byte = data.readByte(True)
                    if byte != 15:
                        raw_input()
                self.map.write(data.read())
            elif packet.id == Ack.id:
                timer = packet.timer
                sequence = packet.sequence2
                try:
                    defer = self.packet_deferreds.pop((sequence, timer))
                    defer.callback(packet)
                except KeyError:
                    raw_input('wut?')
            elif packet.id == Packet10.id:
                print 'received:', packet
            elif packet.id == Ping.id:
                pass
            else:
                print 'received:', packet
                raw_input('unknown packet')