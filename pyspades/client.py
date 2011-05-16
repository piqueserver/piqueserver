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
        
    def sendLoader(self, loader, timer = False, ack = False):
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
            elif packet.id == UserInput.id:
                if self.map is not None:
                    print 'finished!'
                    open('testy.vxl', 'wb').write(str(self.map))
                    self.map = None
                data = packet.data
                firstByte = ord(str(data)[0])
                type = firstByte & 0xF
                print hexify(str(data)), '%r' % str(data), self.in_packet.connectionId
                if type == 8:
                    firstInt = data.readInt(True, False)
                    playerId = (firstInt >> 4) & 0x1F
                    team = (firstInt >> 9) & 9 # team
                    something2 = (firstInt >> 10) & 7 # something?
                    kills = (firstInt >> 13) & 0x7FF # kills
                    data.rewind(1)
                    byte1 = data.readByte(True)
                    byte2 = data.readByte(True)
                    byte3 = data.readByte(True)
                    something4 = byte1 | ((byte2 | (byte3 << 8)) << 8)
                    name = data.read()[:-1]
                    client = OtherClient(self, name, playerId)
                    client.something2 = something2
                    client.kills = kills
                    client.something4 = something4
                    client.team = team
                    self.clients[playerId, name] = client
                elif type == 2:
                    data.skipBytes(1)
                    # movement info
                    playerId = data.readByte(True)
                    something1 = (firstByte >> 4) & 1 # going forward?
                    something2 = (firstByte >> 5) & 1 # going back?
                    something3 = (firstByte >> 6) & 1 # going left?
                    something4 = (firstByte >> 7) # going right?
                    if firstByte & 0xF0:
                        # do something?
                        pass
                    player, = self.clients[playerId]
                    print '2:', player.name, something1, something2, something3, something4
                elif type == 3:
                    data.skipBytes(1)
                    # animation info
                    playerId = data.readByte(True)
                    something1 = (firstByte >> 4) & 1 # mouse button 1
                    something2 = (firstByte >> 5) & 1 # jump
                    something3 = (firstByte >> 6) & 1  # crouch
                    something4 = (firstByte >> 7) # aiming
                    if firstByte & 0xF0:
                        # do something?
                        pass
                    player, = self.clients[playerId]
                    print '3:', player.name, something1, something2, something3, something4
                # sound?
                elif type == 11:
                    firstInt = data.readInt(True, False)
                    something1 = (firstInt >> 6) & 0x1FF # float?
                    something2 = (firstInt >> 15) & 0x1FF
                    something3 = (firstInt >> 24) & 0x3F
                    # 0 -> build sound, 1 -> no idea, 2 -> hitground, 3 -> no idea
                    something4 = (firstInt >> 4) & 3
                    print '11:', something1, something2, something3, something4
                    if something4 == 0:
                        playerId = data.readByte(True)
                elif type == 6:
                    data.skipBytes(1)
                    playerId = data.readByte(True)
                    something1 = firstByte >> 4 # tool
                    # 0 -> spade, 1 -> dagger, 2 -> block, 3 -> gun
                    player, = self.clients[playerId]
                    print '6:', player.name, something1
                elif type == 13:
                    firstShort = data.readShort(True, False)
                    player1 = (firstShort >> 4) & 31
                    player2 = (firstShort >> 9) & 31
                    print '13:', self.clients[player1][0].name, self.clients[player2][0].name
                elif type == 12:
                    if firstByte & 16: # player left
                        data.skipBytes(1)
                        player = data.readByte(1)
                    else:
                        firstInt = data.readInt(True, False)
                        something1 = (firstInt >> 5) & 0x1F
                        something2 = (firstInt >> 10) & 0x3FF
                        something3 = (firstInt >> 20) & 0x3FF
                        if firstInt & 0x40000000:
                            playerId = data.readByte(True)
                        else:
                            byte = data.readByte(True)
                            byte2 = data.readByte(True)
                            byte3 = data.readByte(True)
                            something4 = byte | ((byte2 & 1) << 8)
                            something5 = (byte2 >> 1) | ((byte3 & 3) << 7)
                            something6 = byte3 >> 2
                            if (firstByte >> 31) & 1:
                                playerId = data.readByte(True)
                                data.skipBytes(2)
                            else:
                                byte4 = data.readByte(True)
                                byte5 = data.readByte(True)
                                byte6 = data.readByte(True)
                                something7 = byte4 | ((byte5 & 1) << 8)
                                something8 = (byte5 >> 1) | ((byte6 & 3) << 7)
                                something9 = byte6 >> 2
                            byte7 = data.readByte(True)
                            byte8 = data.readByte(True)
                            byte9 = data.readByte(True)
                            byte10 = data.readByte(True)
                            byte11 = data.readByte(True)
                            byte12 = data.readByte(True)
                            something10 = byte7 | ((byte8 & 1) << 8)
                            something11 = (byte8 >> 1) | ((byte9 & 3) << 7)
                            something12 = byte9 >> 2
                            something13 = byte10 | ((byte11 & 1) << 8)
                            something14 = (byte11 >> 1) | ((byte12 & 3) << 7)
                            something15 = byte12 >> 2
                    print '12!'
                elif type == 10:
                    # new player?
                    firstInt = data.readInt(True, False)
                    if data.dataLeft():
                        name = data.read()[:-1]
                    else:
                        name = None
                    playerId = (firstInt >> 4) & 31
                    something1 = (firstInt >> 9) & 0x1FF
                    something2 = (firstInt >> 18) & 0xFF
                    something3 = (firstInt >> 26) & 0x3F
                    if playerId not in self.clients:
                        client = OtherClient(self, name, playerId)
                        self.clients[name, playerId] = client
                    print '10: new player?', name, playerId, something1, something2, something3
                elif type == 7:
                    firstInt = data.readInt(True, False)
                    playerId = data.readByte(True)
                    something4 = firstInt >> 4
                    print '7:', playerId, something4
                    client, = self.clients[playerId]
                    client.something4 = something4
                    print '7:', client.name, client.name, something4
                elif type == 9:
                    something1 = (firstByte >> 4) & 7
                    if something1 == 0:
                        data.skipBytes(1)
                        byte = data.readByte(True)
                        something2 = byte & 3
                        something3 = byte >> 2
                    elif something1 == 1:
                        data.skipBytes(1)
                        playerId = data.readByte(True)
                    elif something1 == 2: # dropped intel
                        firstInt = data.readInt(True, False)
                        playerId = (firstInt >> 7) & 31
                        something2 = (firstInt >> 12) & 0x1FF
                        something3 = firstInt >> 21
                        something4 = data.readByte(True)
                    elif something1 == 3: # captured intel
                        firstInt = data.readInt(True, False)
                        playerId = (firstInt >> 7) & 0x1F
                        something2 = (firstInt >> 12) & 0x1FF
                        something3 = firstInt >> 21
                        something4 = data.readByte(True)
                    elif something1 == 4:
                        pass
                elif type == 5:
                    data.skipBytes(1)
                    playerId = data.readByte(True)
                    something1 = data.readFloat(False)
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