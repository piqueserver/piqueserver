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

from twisted.internet.protocol import DatagramProtocol
from twisted.internet import reactor
from pyspades.protocol import (BaseConnection, sized_sequence, 
    sized_data, in_packet, out_packet)
from pyspades.bytereader import ByteReader
from pyspades.packet import Packet, load_client_packet
from pyspades.loaders import *
from pyspades.common import *
from pyspades import serverloaders, clientloaders
from pyspades.multidict import MultikeyDict
from pyspades.idpool import IDPool
from pyspades.master import get_master_connection

import random
import math

player_data = serverloaders.PlayerData()
create_player = serverloaders.CreatePlayer()
position_data = serverloaders.PositionData()
orientation_data = serverloaders.OrientationData()
movement_data = serverloaders.MovementData()
animation_data = serverloaders.AnimationData()
hit_packet = serverloaders.HitPacket()
grenade_packet = serverloaders.GrenadePacket()
set_weapon = serverloaders.SetWeapon()
set_color = serverloaders.SetColor()
existing_player = serverloaders.ExistingPlayer()
intel_action = serverloaders.IntelAction()
block_action = serverloaders.BlockAction()
kill_action = serverloaders.KillAction()
chat_message = serverloaders.ChatMessage()

class ServerConnection(BaseConnection):
    protocol = None
    address = None
    player_id = None
    map_packets_sent = 0
    team = None
    name = None
    
    up = down = left = right = False
    position = orientation = None
    fire = jump = aim = crouch = None
    
    def __init__(self, protocol, address):
        BaseConnection.__init__(self)
        self.protocol = protocol
        self.address = address
        self.connection_id = 0
    
    def loader_received(self, loader):
        if loader.id == ConnectionRequest.id:
            if loader.client and loader.version != self.protocol.version:
                self.disconnect()
                return
            self.auth_val = loader.auth_val
            self.player_id = self.protocol.id_pool.pop()
            self.unique = random.randint(0, 3)
            connection_response = ConnectionResponse()
            connection_response.auth_val = loader.auth_val
            connection_response.unique = self.unique
            connection_response.connection_id = self.player_id
            
            self.map_data = ByteReader(self.protocol.map_data)
            self.send_loader(connection_response, True, 0xFF).addCallback(
                self.send_map)
        elif loader.id == Ack.id:
            pass
        elif loader.id == Packet10.id:
            print 'got packet 10'
        elif loader.id == Disconnect.id:
            self.disconnect()
        elif loader.id == Ping.id:
            pass
        elif loader.id in (SizedData.id, SizedSequenceData.id):
            contained = load_client_packet(loader.data)
            if contained.id == clientloaders.JoinTeam.id:
                self.team = [self.protocol.blue_team, 
                    self.protocol.green_team][contained.team]
                self.name = contained.name
                self.protocol.players[self.name, self.player_id] = self
                create_player.name = self.name
                create_player.player_id = self.player_id
                self.orientation = Vertex3(0, 0, 0)
                self.position = position = Vertex3(20, 20, 30)
                create_player.x = position.x
                create_player.y = position.y
                create_player.z = position.z
                self.send_contained(create_player)
            if contained.id == clientloaders.OrientationData.id:
                self.orientation.set(contained.x, contained.y, contained.z)
                orientation_data.x = contained.x
                orientation_data.y = contained.y
                orientation_data.z = contained.z
                orientation_data.player_id = self.player_id
                self.protocol.send_contained(orientation_data, 0)
            elif contained.id == clientloaders.PositionData.id:
                self.position.set(contained.x, contained.y, contained.z)
                position_data.x = contained.x
                position_data.y = contained.y
                position_data.z = contained.z
                position_data.player_id = self.player_id
                self.protocol.send_contained(position_data, sender = self)
            elif contained.id == clientloaders.MovementData.id:
                self.up = contained.up
                self.down = contained.down
                self.left = contained.left
                self.right = contained.right
                movement_data.up = self.up
                movement_data.down = self.down
                movement_data.left = self.left
                movement_data.right = self.right
                movement_data.player_id = self.player_id
                self.protocol.send_contained(movement_data, sender = self)
            elif contained.id == clientloaders.AnimationData.id:
                self.fire = contained.fire
                self.jump = contained.jump
                self.crouch = contained.crouch
                self.aim = contained.aim
                animation_data.fire = self.fire
                animation_data.jump = self.jump
                animation_data.crouch = self.crouch
                animation_data.aim = self.aim
                animation_data.player_id = self.player_id
                self.protocol.send_contained(animation_data, sender = self)
            elif contained.id == clientloaders.HitPacket.id:
                if contained.player_id is not None:
                    player, = self.protocol.players[contained.player_id]
                    hit_packet.value = contained.value
                    player.send_contained(hit_packet)
            elif contained.id == clientloaders.GrenadePacket.id:
                grenade_packet.player_id = self.player_id
                grenade_packet.value = contained.value
                self.protocol.send_contained(grenade_packet, sender = self)
            elif contained.id == clientloaders.SetWeapon.id:
                set_weapon.player_id = self.player_id
                set_weapon.value = contained.value
                self.protocol.send_contained(set_weapon, sender = self)
            elif contained.id == clientloaders.SetColor.id:
                set_color.player_id = self.player_id
                set_color.value = contained.value
                self.protocol.send_contained(set_color, sender = self)
            elif contained.id == clientloaders.BlockAction.id:
                block_action.x = contained.x
                block_action.y = contained.y
                block_action.z = contained.z
                block_action.value = contained.value
                block_action.player_id = self.player_id
                self.protocol.send_contained(block_action)
            elif contained.id == clientloaders.KillAction.id:
                kill_action.player1 = self.player_id
                kill_action.player2 = contained.player_id
                self.protocol.send_contained(kill_action, sender = self)
            elif contained.id == clientloaders.ChatMessage.id:
                chat_message.global_message = contained.global_message
                chat_message.value = contained.value
                chat_message.player_id = self.player_id
                self.protocol.send_contained(chat_message, sender = self)
            else:
                print 'received:', contained
        else:
            print 'received:', loader
            raw_input('unknown loader')
    
    def disconnect(self):
        if self.disconnected:
            return
        BaseConnection.disconnect(self)
        del self.protocol.connections[self.address]
        if self.player_id is not None:
            self.protocol.id_pool.put_back(self.player_id)
        if self.name is not None:
            del self.protocol.players[self]
    
    def send_map(self, ack = None):
        if not self.map_data.dataLeft():
            blue = self.protocol.green_team
            green = self.protocol.green_team
            blue_flag = blue.flag
            green_flag = green.flag
            blue_base = blue.base
            green_base = green.base
            
            player_data.count = 0
            player_data.blue_score = blue.score
            player_data.green_score = green.score
            
            player_data.blue_base_x = blue_base.x
            player_data.blue_base_y = blue_base.y
            player_data.blue_base_z = blue_base.z
            
            player_data.green_base_x = green_base.x
            player_data.green_base_y = green_base.y
            player_data.green_base_z = green_base.z
            
            player_data.blue_flag_x = blue_flag.x
            player_data.blue_flag_y = blue_flag.y
            player_data.blue_flag_z = blue_flag.z
            
            player_data.green_flag_x = green_flag.x
            player_data.green_flag_y = green_flag.y
            player_data.green_flag_z = green_flag.z
            
            self.send_contained(player_data)
            return
        # self.ping()
        sequence = self.packet_handler1.sequence + 1
        data_size = min(4096, self.map_data.dataLeft())
        new_data = ByteReader('\x0F' + self.map_data.read(data_size))
        new_data_size = len(new_data)
        nums = int(math.ceil(new_data_size / 1024.0))
        for i in xrange(nums):
            map_data = MapData()
            map_data.data = new_data.readReader(1024)
            map_data.sequence2 = sequence
            map_data.num = i
            map_data.total_num = nums
            map_data.data_size = new_data_size
            map_data.current_pos = i * 1024
            self.send_loader(map_data, True).addCallback(self.got_map_ack)
            self.map_packets_sent += 1
    
    def got_map_ack(self, ack):
        self.map_packets_sent -= 1
        if not self.map_packets_sent:
            self.send_map()
    
    def send_data(self, data):
        self.protocol.transport.write(data, self.address)

class Vertex3(object):
    def __init__(self, *arg, **kw):
        self.set(*arg, **kw)
    
    def set(self, x, y, z):
        self.x = x
        self.y = y
        self.z = z

class Flag(Vertex3):
    player = None

class Team(object):
    score = 0
    flag = None
    
    def __init__(self, base_pos, flag_pos):
        self.flag = Flag(*flag_pos)
        self.base = Vertex3(*base_pos)

class ServerProtocol(DatagramProtocol):
    name = 'pyspades WIP test'
    max_players = 20

    connections = None
    id_pool = None
    master = None
    
    def __init__(self):
        self.connections = {}
        self.players = MultikeyDict()
        self.id_pool = IDPool()
        self.map_data = open('sinc0.vxl', 'rb').read()
        self.ip_list = []
        ip_list = open('ip_list.txt', 'rb').read().splitlines()
        for ip in ip_list:
            reactor.resolve(ip).addCallback(self.add_ip)
        self.blue_team = Team((20, 20, 20), (40, 40, 40))
        self.green_team = Team((20, 20, 20), (40, 40, 40))
    
    def add_ip(self, ip):
        self.ip_list.append(ip)
        print 'added IP:', ip
    
    def startProtocol(self):
        self.version = crc32(open('client.exe', 'rb').read())
        get_master_connection(self.name, self.max_players).addCallback(
            self.got_master_connection)
        
    def got_master_connection(self, connection):
        self.master = connection
    
    def datagramReceived(self, data, address):
        if address[0] not in self.ip_list:
            return
        if address not in self.connections:
            self.connections[address] = ServerConnection(self, address)
        connection = self.connections[address]
        connection.data_received(data)
    
    def send_contained(self, contained, sequence = None, sender = None):
        if sequence is not None:
            loader = sized_sequence
            loader.sequence2 = sequence
        else:
            loader = sized_data
        data = ByteReader()
        contained.write(data)
        loader.data = data
        for player in self.players.values():
            if player is sender:
                continue
            player.send_loader(loader, sequence is None)