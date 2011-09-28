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
        self.player_id = reader.readByte(True)
        reader.skipBytes(2)
        self.x = reader.readFloat(False)
        self.y = reader.readFloat(False)
        self.z = reader.readFloat(False)
    
    cpdef write(self, ByteWriter reader):
        reader.writeByte(self.id, True)
        reader.writeByte(self.player_id, True)
        reader.pad(2)
        reader.writeFloat(self.x, False)
        reader.writeFloat(self.y, False)
        reader.writeFloat(self.z, False)

cdef class PositionData(_InformationCommon):
    id = 0

cdef class OrientationData(_InformationCommon):
    id = 1

cdef class InputData(Loader):
    id = 2
    cdef public:
        int player_id
        bint up, down, left, right, fire, jump, crouch, aim
    
    cpdef read(self, ByteReader reader):
        self.player_id = reader.readByte(True)
        reader.skipBytes(2)
        cdef int firstByte = reader.readInt(True, False)
        self.up = (firstByte >> 0) & 1
        self.down = (firstByte >> 1) & 1
        self.left = (firstByte >> 2) & 1
        self.right = (firstByte >> 3) & 1
        self.fire = (firstByte >> 4) & 1
        self.jump = (firstByte >> 5) & 1
        self.crouch = (firstByte >> 6) & 1
        self.aim = (firstByte >> 7) & 1
    
    cpdef write(self, ByteWriter reader):
        reader.writeByte(self.id, True)
        reader.writeByte(self.player_id, True)
        reader.pad(2)
        cdef int byte
        byte = (self.up | (self.down << 1) | (self.left << 2) | 
            (self.right << 3) | (self.fire << 4) | (self.jump << 5) |
            (self.crouch << 6) | (self.aim << 7))
        reader.writeInt(byte, True, False)

cdef class HitPacket(Loader):
    id = 4
    
    cdef public:
        int player_id, value
    
    cpdef read(self, ByteReader reader):
        self.player_id = reader.readByte(True)
        reader.skipBytes(2)
        self.value = reader.readInt(True, False)
    
    cpdef write(self, ByteWriter reader):
        reader.writeByte(self.id, True)
        reader.writeByte(self.player_id, True)
        reader.pad(2)
        reader.writeInt(self.value, True, False)

cdef class SetHP(Loader):
    id = 4
    cdef public:
        int hp, hit_indicator, not_fall

    cpdef read(self, ByteReader reader):
        reader.skipBytes(3)
        self.hp = reader.readInt(True, False)
        self.hit_indicator = reader.readInt(True, False)
        # FALL = 0, WEAPON = 1
        self.not_fall = reader.readInt(True, False)
    
    cpdef write(self, ByteWriter reader):
        reader.writeByte(self.id, True)
        reader.pad(3)
        reader.writeInt(self.hp, True, False)
        reader.writeInt(self.hit_indicator, True, False)
        reader.writeInt(self.not_fall, True, False)

cdef class GrenadePacket(Loader):
    id = 5

    cdef public:
        int player_id
        float value
        tuple position, velocity

    cpdef read(self, ByteReader reader):
        self.player_id = reader.readByte(True)
        reader.skipBytes(2)
        self.value = reader.readFloat(False)
        self.position = (reader.readFloat(False), reader.readFloat(False),
            reader.readFloat(False))
        self.velocity = (reader.readFloat(False), reader.readFloat(False),
            reader.readFloat(False))
    
    cpdef write(self, ByteWriter reader):
        reader.writeByte(self.id, True)
        reader.writeByte(self.player_id, True)
        reader.pad(2)
        reader.writeFloat(self.value, False)
        for value in self.position:
            reader.writeFloat(value, False)
        for value in self.velocity:
            reader.writeFloat(value, False)

cdef class SetTool(Loader):
    id = 6
    
    cdef public:
        int player_id, value

    cpdef read(self, ByteReader reader):
        self.player_id = reader.readByte(True)
        reader.skipBytes(2)
        self.value = reader.readInt(True, False)
    
    cpdef write(self, ByteWriter reader):
        reader.writeByte(self.id, True)
        reader.writeByte(self.player_id, True)
        reader.pad(2)
        reader.writeInt(self.value, True, False)

cdef class SetColor(Loader):
    id = 7

    cdef public:
        unsigned int value, player_id

    cpdef read(self, ByteReader reader):
        self.player_id = reader.readByte(True)
        reader.skipBytes(2)
        self.value = reader.readInt(True, False)
    
    cpdef write(self, ByteWriter reader):
        reader.writeByte(self.id, True)
        reader.writeByte(self.player_id, True)
        reader.pad(2)
        reader.writeInt(self.value, True, False)

cdef class ExistingPlayer(Loader):
    id = 8
    
    cdef public:
        int player_id, team, weapon, tool, kills, color
        object name
    
    cpdef read(self, ByteReader reader):
        self.player_id = reader.readByte(True)
        reader.skipBytes(2)
        self.team = reader.readInt(True, False)
        self.weapon = reader.readByte(True)
        self.tool = reader.readByte(True)
        reader.skipBytes(2)
        self.kills = reader.readInt(True, False)
        self.color = reader.readInt(True, False)
        self.name = decode(reader.readString()) # 16 bytes
    
    cpdef write(self, ByteWriter reader):
        reader.writeByte(self.id, True)
        reader.writeByte(self.player_id, True)
        reader.pad(2)
        reader.writeInt(self.team, True, False)
        reader.writeByte(self.weapon, True)
        reader.writeByte(self.tool, True)
        reader.pad(2)
        reader.writeInt(self.kills, True, False)
        reader.writeInt(self.color, True, False)
        reader.writeString(encode(self.name))
    
cdef class MoveObject(Loader):
    id = 9
    
    cdef public:
        unsigned int x, y, z, object_type
    
    cpdef read(self, ByteReader reader):
        reader.skipBytes(3)
        self.x = reader.readInt(True, False)
        self.y = reader.readInt(True, False)
        self.z = reader.readInt(True, False)
        self.object_type = reader.readInt(True, False)
        
    cpdef write(self, ByteWriter reader):
        reader.writeByte(self.id, True)
        reader.pad(3)
        reader.writeInt(self.x, True, False)
        reader.writeInt(self.y, True, False)
        reader.writeInt(self.z, True, False)
        reader.writeInt(self.object_type, True, False)

cdef class CreatePlayer(Loader):
    id = 10
    
    cdef public:
        unsigned int x, y, z, player_id, weapon, team
        object name

    cpdef read(self, ByteReader reader):
        self.player_id = reader.readByte(True)
        reader.skipBytes(2)
        self.team = reader.readInt(True, False)
        self.x = reader.readInt(True, False)
        self.y = reader.readInt(True, False)
        self.z = reader.readInt(True, False)
        self.weapon = reader.readByte(True)
        self.name = decode(reader.readString())
    
    cpdef write(self, ByteWriter reader):
        reader.writeByte(self.id, True)
        reader.writeByte(self.player_id, True)
        reader.pad(2)
        reader.writeInt(self.team, True, False)
        reader.writeInt(self.x, True, False)
        reader.writeInt(self.y, True, False)
        reader.writeInt(self.z, True, False)
        reader.writeByte(self.weapon, True)
        reader.writeString(encode(self.name))

cdef class BlockAction(Loader):
    id = 11
    
    cdef public:
        unsigned int x, y, z, value, player_id

    cpdef read(self, ByteReader reader):
        self.player_id = reader.readByte(True)
        reader.skipBytes(2)
        self.x = reader.readInt(True, False)
        self.y = reader.readInt(True, False)
        self.z = reader.readInt(True, False)
        self.value = reader.readInt(True, False)
    
    cpdef write(self, ByteWriter reader):
        reader.writeByte(self.id, True)
        reader.writeByte(self.player_id, True)
        reader.pad(2)
        reader.writeInt(self.x, True, False)
        reader.writeInt(self.y, True, False)
        reader.writeInt(self.z, True, False)
        reader.writeInt(self.value, True, False)

cdef class CTFState(Loader):
    id = 0
    
    cdef public:
        int team1_score, team2_score, cap_limit
        bint team1_has_intel, team2_has_intel
        int team1_carrier, team1_flag_x, team1_flag_y, team1_flag_z
        int team2_carrier, team2_flag_x, team2_flag_y, team2_flag_z
        int team1_base_x, team1_base_y, team1_base_z
        int team2_base_x, team2_base_y, team2_base_z
    
    cpdef read(self, ByteReader reader):
        self.team1_score = reader.readInt(True, False)
        self.team2_score = reader.readInt(True, False)
        self.cap_limit = reader.readInt(True, False)
        cdef int intel_flags = reader.readByte(True)
        reader.skipBytes(3)
        self.team1_has_intel = intel_flags & 1
        self.team2_has_intel = (intel_flags >> 1) & 1
        if self.team1_has_intel:
            self.team1_carrier = reader.readByte(True)
            reader.skipBytes(12 - 1)
        else:
            self.team1_flag_x = reader.readInt(True, False)
            self.team1_flag_y = reader.readInt(True, False)
            self.team1_flag_z = reader.readInt(True, False)
        
        if self.team2_has_intel:
            self.team2_carrier = reader.readByte(True)
            reader.skipBytes(12 - 1)
        else:
            self.team2_flag_x = reader.readInt(True, False)
            self.team2_flag_y = reader.readInt(True, False)
            self.team2_flag_z = reader.readInt(True, False)
        
        self.team1_base_x = reader.readInt(True, False)
        self.team1_base_y = reader.readInt(True, False)
        self.team1_base_z = reader.readInt(True, False)
        
        self.team2_base_x = reader.readInt(True, False)
        self.team2_base_y = reader.readInt(True, False)
        self.team2_base_z = reader.readInt(True, False)
    
    cpdef write(self, ByteWriter reader):
        reader.writeInt(self.team1_score, True, False)
        reader.writeInt(self.team2_score, True, False)
        reader.writeInt(self.cap_limit, True, False)
        cdef int intel_flags = (self.team1_has_intel | (
            self.team2_has_intel << 1))
        reader.writeByte(intel_flags, True)
        reader.pad(3)
        if self.team1_has_intel:
            reader.writeByte(self.team1_carrier, True)
            reader.pad(11)
        else:
            reader.writeInt(self.team1_flag_x, True, False)
            reader.writeInt(self.team1_flag_y, True, False)
            reader.writeInt(self.team1_flag_z, True, False)
        
        if self.team2_has_intel:
            reader.writeByte(self.team2_carrier, True)
            reader.pad(11)
        else:
            reader.writeInt(self.team2_flag_x, True, False)
            reader.writeInt(self.team2_flag_y, True, False)
            reader.writeInt(self.team2_flag_z, True, False)
        
        reader.writeInt(self.team1_base_x, True, False)
        reader.writeInt(self.team1_base_y, True, False)
        reader.writeInt(self.team1_base_z, True, False)
        
        reader.writeInt(self.team2_base_x, True, False)
        reader.writeInt(self.team2_base_y, True, False)
        reader.writeInt(self.team2_base_z, True, False)
    
modes = {
    0 : CTFState
}

cdef class StateData(Loader):
    id = 12
    
    cdef public:
        int player_id
        tuple fog_color
        Loader state

    cpdef read(self, ByteReader reader):
        self.player_id = reader.readByte(True)
        self.fog_color = (reader.readByte(True), reader.readByte(True),
            reader.readByte(True))
        reader.skipBytes(3)
        cdef int mode = reader.readInt(True, False)
        self.state = modes[mode](reader)
        
    cpdef write(self, ByteWriter reader):
        reader.writeByte(self.id, True)
        reader.writeByte(self.player_id, True)
        for value in self.fog_color:
            reader.writeByte(value, True)
        reader.pad(3)
        reader.writeInt(self.state.id, True, False)
        self.state.write(reader)

cdef class KillAction(Loader):
    id = 13
    
    cdef public:
        int player_id, killer_id, kill_type
    
    cpdef read(self, ByteReader reader):
        self.player_id = reader.readByte(True)
        self.killer_id = reader.readByte(True)
        reader.skipBytes(1)
        self.kill_type = reader.readInt(True, False)
    
    cpdef write(self, ByteWriter reader):
        reader.writeByte(self.id, True)
        reader.writeByte(self.player_id, True)
        reader.writeByte(self.killer_id, True)
        reader.pad(1)
        reader.writeInt(self.kill_type, True, False)

cdef class ChatMessage(Loader):
    id = 14
    
    cdef public:
        unsigned int player_id, chat_type
        object value
    
    cpdef read(self, ByteReader reader):
        self.player_id = reader.readByte(True)
        reader.skipBytes(2)
        self.chat_type = reader.readInt(True, False)
        self.value = decode(reader.readString())
    
    cpdef write(self, ByteWriter reader):
        reader.writeByte(self.id, True)
        reader.writeByte(self.player_id, True)
        reader.pad(2)
        reader.writeInt(self.chat_type, True, False)
        reader.writeString(encode(self.value))

cdef class MapStart(Loader):
    id = 15
    
    cdef public:
        unsigned int size
    
    cpdef read(self, ByteReader reader):
        reader.skipBytes(3)
        self.size = reader.readInt(True, False)
    
    cpdef write(self, ByteWriter reader):
        reader.writeByte(self.id, True)
        reader.pad(3)
        reader.writeInt(self.size, True, False)

cdef class MapChunk(Loader):
    id = 16
    
    cdef public:
        object data
    
    cpdef read(self, ByteReader reader):
        self.data = reader.read()
    
    cpdef write(self, ByteWriter reader):
        reader.writeByte(self.id, True)
        reader.write(self.data)

cdef class PlayerLeft(Loader):
    id = 17
    
    cdef public:
        int player_id
    
    cpdef read(self, ByteReader reader):
        self.player_id = reader.readByte(True)
    
    cpdef write(self, ByteWriter reader):
        reader.writeByte(self.id, True)
        reader.writeByte(self.player_id, True)

cdef class IntelCapture(Loader):
    id = 18
    
    cdef public:
        int player_id
        bint winning
    
    cpdef read(self, ByteReader reader):
        self.player_id = reader.readByte(True)
        self.winning = reader.readByte(True)
    
    cpdef write(self, ByteWriter reader):
        reader.writeByte(self.id, True)
        reader.writeByte(self.player_id, True)
        reader.writeByte(self.winning, True)

cdef class IntelPickup(Loader):
    id = 19
    
    cdef public:
        int player_id
    
    cpdef read(self, ByteReader reader):
        self.player_id = reader.readByte(True)
    
    cpdef write(self, ByteWriter reader):
        reader.writeByte(self.id, True)
        reader.writeByte(self.player_id, True)

cdef class IntelDrop(Loader):
    id = 20
    
    cdef public:
        int player_id, x, y, z
    
    cpdef read(self, ByteReader reader):
        self.player_id = reader.readByte(True)
        reader.skipBytes(2)
        self.x = reader.readInt(True, False)
        self.y = reader.readInt(True, False)
        self.z = reader.readInt(True, False)
    
    cpdef write(self, ByteWriter reader):
        reader.writeByte(self.id, True)
        reader.writeByte(self.player_id, True)
        reader.pad(2)
        reader.writeByte(self.x, True)
        reader.writeByte(self.y, True)
        reader.writeByte(self.z, True)

cdef class Restock(Loader):
    id = 21
    
    cdef public:
        int player_id
    
    cpdef read(self, ByteReader reader):
        self.player_id = reader.readByte(True)
    
    cpdef write(self, ByteWriter reader):
        reader.writeByte(self.id, True)
        reader.writeByte(self.player_id, True)

cdef class FogColor(Loader):
    id = 22
    
    cdef public:
        int color
    
    cpdef read(self, ByteReader reader):
        reader.skipBytes(3)
        self.color = reader.readInt(True, False) >> 5
    
    cpdef write(self, ByteWriter reader):
        reader.writeByte(self.id, True)
        reader.pad(3)
        reader.writeInt(self.color << 5, True, False)

cdef class WeaponReload(Loader):
    id = 23
    
    cdef public:
        int player_id
    
    cpdef read(self, ByteReader reader):
        self.player_id = reader.readByte(True)
    
    cpdef write(self, ByteWriter reader):
        reader.writeByte(self.id, True)
        reader.writeByte(self.player_id, True)

cdef class ChangeTeam(Loader):
    id = 24
    cdef public:
        int player_id, team

    cpdef read(self, ByteReader reader):
        self.player_id = reader.readByte(True)
        reader.skipBytes(2)
        self.team = reader.readInt(True, False)
    
    cpdef write(self, ByteWriter reader):
        reader.writeByte(self.id, True)
        reader.writeByte(self.player_id, True)
        reader.pad(2)
        reader.writeInt(self.team, True, False)

cdef class ChangeWeapon(Loader):
    id = 25
    cdef public:
        int player_id, weapon

    cpdef read(self, ByteReader reader):
        self.player_id = reader.readByte(True)
        reader.skipBytes(2)
        self.weapon = reader.readInt(True, False)
    
    cpdef write(self, ByteWriter reader):
        reader.writeByte(self.id, True)
        reader.writeByte(self.player_id, True)
        reader.pad(2)
        reader.writeInt(self.weapon, True, False)