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

from pyspades.common import *
from pyspades.loaders cimport Loader
from pyspades.bytes cimport ByteReader, ByteWriter

cdef class _InformationCommon(Loader):
    cdef public:
        int player_id
        float x, y, z

    def set(self, pos, player_id):
        cdef float x, y, z
        x, y, z = pos
        self.x = x
        self.y = y
        self.z = z
        self.player_id = player_id
    
    cpdef read(self, ByteReader reader):
        reader.skipBytes(1)
        self.player_id = reader.readByte(True)
        self.x = reader.readFloat(False) # x
        self.y = reader.readFloat(False) # y
        self.z = reader.readFloat(False) # z
    
    cpdef write(self, ByteWriter reader):
        reader.writeByte(self.id, True)
        reader.writeByte(self.player_id, True)
        reader.writeFloat(self.x, False)
        reader.writeFloat(self.y, False)
        reader.writeFloat(self.z, False)

cdef class PositionData(_InformationCommon):
    id = 0

cdef class OrientationData(_InformationCommon):
    id = 1

cdef class MovementData(Loader):
    id = 2

    cdef public:
        int player_id
        bint up, down, left, right

    cpdef read(self, ByteReader reader):
        cdef int firstByte = reader.readByte(True)
        self.player_id = reader.readByte(True)
        self.up = (firstByte >> 4) & 1 # going forward?
        self.down = (firstByte >> 5) & 1 # going back?
        self.left = (firstByte >> 6) & 1 # going left?
        self.right = (firstByte >> 7) # going right?
    
    cpdef write(self, ByteWriter reader):
        cdef int up = self.up
        cdef int down = self.down
        cdef int left = self.left
        cdef int right = self.right
        cdef int byte = self.id | (up << 4) | (down << 5) | (left << 6) | (
            right << 7)
        reader.writeByte(byte, True)
        reader.writeByte(self.player_id, True)

cdef class AnimationData(Loader):
    id = 3
    
    cdef public:
        int player_id
        bint fire, jump, crouch, aim

    cpdef read(self, ByteReader reader):
        cdef int firstByte = reader.readByte(True)
        self.player_id = reader.readByte(True)
        self.fire = (firstByte >> 4) & 1
        self.jump = (firstByte >> 5) & 1
        self.crouch = (firstByte >> 6) & 1
        self.aim = (firstByte >> 7)
    
    cpdef write(self, ByteWriter reader):
        cdef int fire = self.fire
        cdef int jump = self.jump
        cdef int crouch = self.crouch
        cdef int aim = self.aim
        cdef int byte = self.id | (fire << 4) | (jump << 5) | (crouch << 6) | (
            aim << 7)
        reader.writeByte(byte, True)
        reader.writeByte(self.player_id, True)

cdef class HitPacket(Loader):
    id = 4
    
    cdef public:
        int hp
        bint sound

    cpdef read(self, ByteReader reader):
        cdef int firstByte = reader.readByte(True)
        self.sound = (firstByte & 0xF0) != 0
        self.hp = reader.readByte(True)
    
    cpdef write(self, ByteWriter reader):
        cdef int byte = self.id
        if self.sound:
            byte |= 0x10
        reader.writeByte(byte, True)
        reader.writeByte(self.hp, True)

cdef class GrenadePacket(Loader):
    id = 5
    
    cdef public:
        int player_id
        float value

    cpdef read(self, ByteReader reader):
        reader.skipBytes(1)
        self.player_id = reader.readByte(True)
        self.value = reader.readFloat(False)
    
    cpdef write(self, ByteWriter reader):
        reader.writeByte(self.id, True)
        reader.writeByte(self.player_id, True)
        reader.writeFloat(self.value, False)

cdef class SetWeapon(Loader):
    id = 6
    
    cdef public:
        int player_id, value

    cpdef read(self, ByteReader reader):
        cdef int firstByte = reader.readByte(True)
        self.player_id = reader.readByte(True)
        self.value = firstByte >> 4 # tool
        # 0 -> spade, 1 -> dagger, 2 -> block, 3 -> gun
    
    cpdef write(self, ByteWriter reader):
        cdef int byte = self.id
        byte |= self.value << 4
        reader.writeByte(byte, True)
        reader.writeByte(self.player_id, True)

cdef class SetColor(Loader):
    id = 7

    cdef public:
        unsigned int value, player_id

    cpdef read(self, ByteReader reader):
        cdef unsigned int firstInt = reader.readInt(True, False)
        self.player_id = reader.readByte(True)
        self.value = firstInt >> 4
    
    cpdef write(self, ByteWriter reader):
        cdef unsigned int value = self.id
        value |= self.value << 4
        reader.writeInt(value, True, False)
        reader.writeByte(self.player_id, True)

cdef class ExistingPlayer(Loader):
    id = 8
    
    cdef public:
        int player_id, team, weapon, tool, kills, color
        object name
    
    cpdef read(self, ByteReader reader):
        cdef unsigned char byte1, byte2, byte3
        cdef unsigned int firstInt
        if reader.dataLeft() == 2:
            byte1 = reader.readByte(True)
            self.player_id = reader.readByte(True)
            self.team = (byte1 >> 4) & 1
            self.weapon = byte1 >> 5
        else:
            firstInt = reader.readInt(True, False)
            self.player_id = (firstInt >> 4) & 0x1F
            self.team = (firstInt >> 9) & 1 # team
            self.weapon = (firstInt >> 10) & 1 # weapon
            self.tool = (firstInt >> 11) & 0x7 # something?
            self.kills = (firstInt >> 14) & 0x7FF # kills
            reader.rewind(1)
            byte1 = reader.readByte(True)
            byte2 = reader.readByte(True)
            byte3 = reader.readByte(True)
            self.color = byte1 | ((byte2 | (byte3 << 8)) << 8)
            self.name = decode(reader.readString())
    
    cpdef write(self, ByteWriter reader):
        cdef unsigned int value = self.id
        cdef unsigned char byte1, byte2, byte3
        if self.name is None:
            value |= self.team << 4
            value |= self.weapon << 5
            reader.writeByte(value, True)
            reader.writeByte(self.player_id, True)
        else:
            value |= self.player_id << 4
            value |= self.team << 9
            value |= self.weapon << 10
            value |= (self.tool or 0) << 11
            value |= (self.kills & 0x7FF) << 14
            byte1 = self.color & 0xFF
            byte2 = (self.color & 0xFF00) >> 8
            byte3 = (self.color & 0xFF0000) >> 16
            reader.writeInt(value, True, False)
            reader.rewind(1)
            reader.writeByte(byte1, True)
            reader.writeByte(byte2, True)
            reader.writeByte(byte3, True)
            reader.writeString(encode(self.name))

cdef class IntelAction(Loader):
    id = 9
    
    cdef public:
        int player_id, action_type, x, y, z, move_type
        int blue_flag_x, blue_flag_y, green_flag_x, green_flag_y
        int blue_base_x, blue_base_y, green_base_x, green_base_y
        bint game_end
    
    cpdef read(self, ByteReader reader):
        cdef int firstByte = reader.readByte(True)
        cdef int action_type
        self.action_type = action_type = (firstByte >> 4) & 7
        cdef unsigned int firstInt, secondInt, firstShort
        cdef int byte
        if action_type == 0:
            byte = reader.readByte(True)
            self.move_type = byte & 3
            # 0 -> move blue flag
            # 1 -> move green flag
            # 2 -> move blue base
            # 3 -> move green base
            self.z = byte >> 2 # z
        elif action_type == 1: # taken intel
            self.player_id = reader.readByte(True)
        elif action_type == 2: # dropped intel
            reader.rewind(1)
            firstInt = reader.readInt(True, False)
            self.player_id = (firstInt >> 7) & 31
            self.x = (firstInt >> 12) & 0x1FF # x?
            self.y = firstInt >> 21 # y?
            self.z = reader.readByte(True) # z?
        elif action_type == 3: # captured intel
            reader.rewind(1)
            firstInt = reader.readInt(True, False)
            self.player_id = (firstInt >> 7) & 0x1F
            if firstInt & 0x1000: # end of game
                self.game_end = True
                secondInt = reader.readInt(True, False)
                firstShort = reader.readShort(True, False)
                self.blue_flag_x = (firstInt >> 13) & 0x7F
                self.blue_flag_y = (firstInt >> 20) & 0xFF + 128
                
                self.green_flag_x = secondInt & 0x7F + 384
                self.green_flag_y = (secondInt >> 7) & 0xFF + 128
                
                self.blue_base_x = (secondInt >> 15) & 0x7F 
                self.blue_base_y = (secondInt >> 22) & 0xFF + 128
                
                self.green_base_x = firstShort & 0x7F + 384
                self.green_base_y = (firstShort >> 7) & 0xFF + 128
            else: # normal got intel
                self.game_end = False
                self.x = (firstInt >> 13) & 0x1FF # x?
                self.y = firstInt >> 22 # y?
        elif action_type == 4: # give ammo, health, etc.
            pass
        
    cpdef write(self, ByteWriter reader):
        cdef unsigned int value = self.id | (self.action_type << 4)
        cdef int byte
        if self.action_type == 0:
            reader.writeByte(value, True)
            byte = self.move_type | (self.z << 2)
            reader.writeByte(byte, True)
        elif self.action_type == 1:
            reader.writeByte(value, True)
            reader.writeByte(self.player_id, True)
        elif self.action_type == 2:
            value |= self.player_id << 7
            value |= self.x << 12
            value |= self.y << 21
            reader.writeInt(value, True, False)
            reader.writeByte(self.z, True)
        elif self.action_type == 3:
            value |= self.player_id << 7
            if self.game_end:
                value |= 0x1000
                value |= self.blue_flag_x << 13
                value |= (self.blue_flag_y - 128) << 20
                reader.writeInt(value, True, False)
                value2 = self.green_flag_x - 384
                value2 |= (self.green_flag_y - 128) << 7
                value2 |= self.blue_base_x << 15
                value2 |= (self.blue_base_y - 128) << 22
                reader.writeInt(value2, True, False)
                value3 = (self.green_base_x - 384)
                value3 |= (self.green_base_y - 128) << 7
                reader.writeShort(value3, True, False)
            else:
                value |= self.x << 13
                value |= self.y << 22
                reader.writeInt(value, True, False)
        elif self.action_type == 4: # give ammo
            reader.writeByte(value, True)

cdef class CreatePlayer(Loader):
    id = 10
    
    cdef public:
        int x, y, player_id, weapon
        object name

    cpdef read(self, ByteReader reader):
        # new player + spawn player
        cdef unsigned int firstInt = reader.readInt(True, False)
        if reader.dataLeft():
            self.name = decode(reader.readString())
        self.player_id = (firstInt >> 4) & 31
        self.x = (firstInt >> 9) & 0x1FF
        self.y = (firstInt >> 18) & 0xFF
        self.weapon = (firstInt >> 26) & 0x1
    
    cpdef write(self, ByteWriter reader):
        cdef unsigned int value = self.id
        value |= self.player_id << 4
        value |= self.x << 9
        value |= self.y << 18
        value |= self.weapon << 26
        reader.writeInt(value, True, False)
        if self.name is not None:
            reader.writeString(encode(self.name))

cdef class BlockAction(Loader):
    id = 11
    
    cdef public:
        unsigned int x, y, z, value, player_id

    cpdef read(self, ByteReader reader):
        cdef unsigned int firstInt = reader.readInt(True, False)
        self.x = (firstInt >> 6) & 0x1FF # x
        self.y = (firstInt >> 15) & 0x1FF # y
        self.z = (firstInt >> 24) & 0x3F # z
        # 0 -> build, 1 -> destroy, 2 -> spade destroy, 3 -> grenade destroy
        self.value = (firstInt >> 4) & 3
        if self.value == 0:
            self.player_id = reader.readByte(True)
    
    cpdef write(self, ByteWriter reader):
        cdef unsigned int value
        value = (self.id | (self.x << 6) | (self.y << 15) | (self.z << 24) |
            (self.value << 4))
        reader.writeInt(value, True, False)
        if self.value == 0:
            reader.writeByte(self.player_id, True)

cdef inline tuple make_coordinate_bytes(int x, int y, int z):
    cdef unsigned char byte1, byte2, byte3
    byte1 = x & 0xFF
    byte2 = (x >> 8) | ((y << 1) & 0xFF)
    byte3 = (y >> 7) | (z << 2)
    return byte1, byte2, byte3

cdef class PlayerData(Loader):
    id = 12
    
    cdef public:
        int player_left
        int blue_base_x, blue_base_y, blue_base_z
        int green_base_x, green_base_y, green_base_z
        int blue_flag_x, blue_flag_y, blue_flag_z, blue_flag_player
        int green_flag_x, green_flag_y, green_flag_z, green_flag_player
        int max_score, blue_score, green_score
        int player_id

    cpdef read(self, ByteReader reader):
        cdef int firstByte = reader.readByte(True)
        cdef unsigned int firstInt
        cdef unsigned char byte, byte2, byte3, byte4, byte5, byte6
        cdef unsigned char byte7, byte8, byte9, byte10, byte11, byte12
        if firstByte & 16: # player left
            self.player_left = reader.readByte(True)
        else:
            self.player_left = -1
            reader.rewind(1)
            # initial reader
            firstInt = reader.readInt(True, False)
            self.player_id = (firstInt >> 5) & 0x1F # player id
            self.blue_score = (firstInt >> 10) & 0x3F # team score 1?
            self.green_score = (firstInt >> 16) & 0x3F # team score 2?
            self.max_score = (firstInt >> 22) & 0x3F
            if firstInt & 0x40000000:
                self.green_flag_player = reader.readByte(True)
                reader.skipBytes(2)
            else:
                self.green_flag_player = -1
                byte = reader.readByte(True)
                byte2 = reader.readByte(True)
                byte3 = reader.readByte(True)
                self.green_flag_x = byte | ((byte2 & 1) << 8)
                self.green_flag_y = (byte2 >> 1) | ((byte3 & 3) << 7)
                self.green_flag_z = byte3 >> 2
            if firstInt & 0x80000000:
                self.blue_flag_player = reader.readByte(True)
                reader.skipBytes(2)
            else:
                self.blue_flag_player = -1
                byte4 = reader.readByte(True)
                byte5 = reader.readByte(True)
                byte6 = reader.readByte(True)
                self.blue_flag_x = byte4 | ((byte5 & 1) << 8)
                self.blue_flag_y = (byte5 >> 1) | ((byte6 & 3) << 7)
                self.blue_flag_z = byte6 >> 2
            byte7 = reader.readByte(True)
            byte8 = reader.readByte(True)
            byte9 = reader.readByte(True)
            byte10 = reader.readByte(True)
            byte11 = reader.readByte(True)
            byte12 = reader.readByte(True)
            self.blue_base_x = byte7 | ((byte8 & 1) << 8)
            self.blue_base_y = (byte8 >> 1) | ((byte9 & 3) << 7)
            self.blue_base_z = byte9 >> 2
            self.green_base_x = byte10 | ((byte11 & 1) << 8)
            self.green_base_y = (byte11 >> 1) | ((byte12 & 3) << 7)
            self.green_base_z = byte12 >> 2
        
    cpdef write(self, ByteWriter reader):
        cdef unsigned int value = self.id
        cdef unsigned char a, b, c
        if self.player_left != -1:
            value |= 16
            reader.writeByte(value, True)
            reader.writeByte(self.player_left, True)
        else:
            value |= (self.player_id << 5)
            value |= (self.blue_score << 10)
            value |= (self.green_score << 16)
            value |= (self.max_score << 22)
            if self.green_flag_player != -1:
                value |= 0x40000000
            if self.blue_flag_player != -1:
                value |= 0x80000000
            reader.writeInt(value, True, False)
            if self.green_flag_player != -1:
                reader.writeByte(self.green_flag_player, True)
                reader.writeByte(0)
                reader.writeByte(0)
            else:
                a, b, c = make_coordinate_bytes(self.green_flag_x,
                    self.green_flag_y, self.green_flag_z)
                reader.writeByte(a, True)
                reader.writeByte(b, True)
                reader.writeByte(c, True)
            if self.blue_flag_player != -1:
                reader.writeByte(self.blue_flag_player, True)
                reader.writeByte(0)
                reader.writeByte(0)
            else:
                a, b, c = make_coordinate_bytes(self.blue_flag_x,
                    self.blue_flag_y, self.blue_flag_z)
                reader.writeByte(a, True)
                reader.writeByte(b, True)
                reader.writeByte(c, True)
            a, b, c = make_coordinate_bytes(self.blue_base_x,
                self.blue_base_y, self.blue_base_z)
            reader.writeByte(a, True)
            reader.writeByte(b, True)
            reader.writeByte(c, True)
            a, b, c = make_coordinate_bytes(self.green_base_x,
                self.green_base_y, self.green_base_z)
            reader.writeByte(a, True)
            reader.writeByte(b, True)
            reader.writeByte(c, True)

cdef class KillAction(Loader):
    id = 13
    
    cdef public:
        bint other_kill
        int player1, player2
    
    cpdef read(self, ByteReader reader):
        cdef int firstShort = reader.readShort(True, False)
        self.other_kill = (firstShort >> 4) & 1
        self.player2 = (firstShort >> 5) & 0x1F
        self.player1 = (firstShort >> 10) & 0x1F
    
    cpdef write(self, ByteWriter reader):
        cdef int value = self.id
        if self.other_kill:
            value |= 1 << 4
        value |= self.player2 << 5
        value |= self.player1 << 10
        reader.writeShort(value, True, False)

cdef class ChatMessage(Loader):
    id = 14
    
    cdef public:
        bint global_message
        int player_id
        object value
    
    cpdef read(self, ByteReader reader):
        cdef int firstByte = reader.readByte(True)
        self.global_message = (firstByte & 0xF0) != 32
        if firstByte & 0xF0:
            self.player_id = reader.readByte(True)
            self.global_message = (firstByte & 0xF0) != 32
        else:
            self.player_id = -1
        self.value = decode(reader.readString())
    
    cpdef write(self, ByteWriter reader):
        cdef int byte = self.id
        if self.player_id != -1:
            if self.global_message:
                byte |= 16
            else:
                byte |= 32
        reader.writeByte(byte, True)
        if self.player_id != -1:
            reader.writeByte(self.player_id, True)
        reader.writeString(encode(self.value))