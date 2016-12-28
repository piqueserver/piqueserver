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

from pyspades.common import *
from pyspades.constants import *
from pyspades.loaders cimport Loader
from pyspades.bytes cimport ByteReader, ByteWriter

cdef inline float limit(float a):
    if a > 512.0:
        return 512.0
    elif a < 0.0:
        return 0.0
    return a

cdef inline void read_position(ByteReader reader, float * x, float * y, 
                               float * z):
    x[0] = reader.readFloat(False)
    y[0] = reader.readFloat(False)
    z[0] = reader.readFloat(False)

cdef inline void write_position(ByteWriter reader, float x, float y, float z):
    reader.writeFloat(x, False)
    reader.writeFloat(y, False)
    reader.writeFloat(z, False)

cdef inline unsigned int read_color(ByteReader reader):
    cdef unsigned char r, g, b
    b = reader.readByte(True)
    g = reader.readByte(True)
    r = reader.readByte(True)
    return (b | (g << 8) | (r << 16))
    
cdef inline void write_color(ByteWriter reader, unsigned int value):
    reader.writeByte(value & 0xFF)
    reader.writeByte((value >> 8) & 0xFF)
    reader.writeByte((value >> 16) & 0xFF)

import itertools
id_iter = itertools.count()

cdef class PositionData(Loader):
    id = id_iter.next()
    
    cdef public:
        float x, y, z

    def set(self, pos):
        cdef float x, y, z
        x, y, z = pos
        self.x = x
        self.y = y
        self.z = z
        
    cpdef read(self, ByteReader reader):
        read_position(reader, &self.x, &self.y, &self.z)
    
    cpdef write(self, ByteWriter reader):
        reader.writeByte(self.id, True)
        write_position(reader, self.x, self.y, self.z)

cdef class OrientationData(Loader):
    id = id_iter.next()
    
    cdef public:
        float x, y, z

    def set(self, pos):
        cdef float x, y, z
        x, y, z = pos
        self.x = x
        self.y = y
        self.z = z
        
    cpdef read(self, ByteReader reader):
        self.x = reader.readFloat(False)
        self.y = reader.readFloat(False)
        self.z = reader.readFloat(False)
    
    cpdef write(self, ByteWriter reader):
        reader.writeByte(self.id, True)
        reader.writeFloat(self.x, False)
        reader.writeFloat(self.y, False)
        reader.writeFloat(self.z, False)

cdef class WorldUpdate(Loader):
    id = id_iter.next()
    
    cdef public:
        list items
    
    cpdef read(self, ByteReader reader):
        cdef list items = []
        self.items = items
        for _ in range(32):
            p_x = reader.readFloat(False)
            p_y = reader.readFloat(False)
            p_z = reader.readFloat(False)
            o_x = reader.readFloat(False)
            o_y = reader.readFloat(False)
            o_z = reader.readFloat(False)
            items.append(((p_x, p_y, p_z), (o_x, o_y, o_z)))
    
    cpdef write(self, ByteWriter reader):
        reader.writeByte(self.id, True)
        cdef tuple item
        for item in self.items:
            (p_x, p_y, p_z), (o_x, o_y, o_z) = item
            reader.writeFloat(p_x, False)
            reader.writeFloat(p_y, False)
            reader.writeFloat(p_z, False)
            reader.writeFloat(o_x, False)
            reader.writeFloat(o_y, False)
            reader.writeFloat(o_z, False)

cdef class InputData(Loader):
    id = id_iter.next()
    cdef public:
        int player_id
        bint up, down, left, right, jump, crouch, sneak, sprint
    
    cpdef read(self, ByteReader reader):
        self.player_id = reader.readByte(True)
        cdef int firstByte = reader.readByte(True)
        self.up = (firstByte >> 0) & 1
        self.down = (firstByte >> 1) & 1
        self.left = (firstByte >> 2) & 1
        self.right = (firstByte >> 3) & 1
        self.jump = (firstByte >> 4) & 1
        self.crouch = (firstByte >> 5) & 1
        self.sneak = (firstByte >> 6) & 1
        self.sprint = (firstByte >> 7) & 1
    
    cpdef write(self, ByteWriter reader):
        reader.writeByte(self.id, True)
        reader.writeByte(self.player_id, True)
        cdef int byte
        byte = (self.up | (self.down << 1) | (self.left << 2) | 
            (self.right << 3) | (self.jump << 4) | (self.crouch << 5) |
            (self.sneak << 6) | (self.sprint << 7))
        reader.writeByte(byte, True)

cdef class WeaponInput(Loader):
    id = id_iter.next()
    
    cdef public:
        bint primary, secondary
        int player_id

    cpdef read(self, ByteReader reader):
        self.player_id = reader.readByte(True)
        cdef unsigned char byte = reader.readByte(True)
        self.primary = byte & 1
        self.secondary = (byte >> 1) & 1
        
    cpdef write(self, ByteWriter reader):
        reader.writeByte(self.id, True)
        reader.writeByte(self.player_id, True)
        cdef unsigned char byte = self.primary | (self.secondary << 1)
        reader.writeByte(byte, True)

hurt_id = id_iter.next()

cdef class HitPacket(Loader):
    id = hurt_id
    
    cdef public:
        int player_id, value
    
    cpdef read(self, ByteReader reader):
        self.player_id = reader.readByte(True)
        self.value = reader.readByte(True)
    
    cpdef write(self, ByteWriter reader):
        reader.writeByte(self.id, True)
        reader.writeByte(self.player_id, True)
        reader.writeByte(self.value, True)

cdef class SetHP(Loader):
    id = hurt_id

    cdef public:
        int hp, not_fall
        float source_x, source_y, source_z

    cpdef read(self, ByteReader reader):
        self.hp = reader.readByte(True)
        # FALL = 0, WEAPON = 1
        self.not_fall = reader.readByte(True)
        self.source_x = reader.readFloat(False)
        self.source_y = reader.readFloat(False)
        self.source_z = reader.readFloat(False)
    
    cpdef write(self, ByteWriter reader):
        reader.writeByte(self.id, True)
        reader.writeByte(self.hp, True)
        reader.writeByte(self.not_fall, True)
        reader.writeFloat(self.source_x, False)
        reader.writeFloat(self.source_y, False)
        reader.writeFloat(self.source_z, False)

cdef class GrenadePacket(Loader):
    id = id_iter.next()

    cdef public:
        int player_id
        float value
        tuple position, velocity

    cpdef read(self, ByteReader reader):
        self.player_id = reader.readByte(True)
        self.value = reader.readFloat(False)
        self.position = (reader.readFloat(False), reader.readFloat(False),
            reader.readFloat(False))
        self.velocity = (reader.readFloat(False), reader.readFloat(False),
            reader.readFloat(False))
    
    cpdef write(self, ByteWriter reader):
        reader.writeByte(self.id, True)
        reader.writeByte(self.player_id, True)
        reader.writeFloat(self.value, False)
        for value in self.position:
            reader.writeFloat(value, False)
        for value in self.velocity:
            reader.writeFloat(value, False)

cdef class SetTool(Loader):
    id = id_iter.next()
    
    cdef public:
        int player_id, value

    cpdef read(self, ByteReader reader):
        self.player_id = reader.readByte(True)
        self.value = reader.readByte(True)
    
    cpdef write(self, ByteWriter reader):
        reader.writeByte(self.id, True)
        reader.writeByte(self.player_id, True)
        reader.writeByte(self.value, True)

cdef class SetColor(Loader):
    id = id_iter.next()

    cdef public:
        unsigned int value, player_id

    cpdef read(self, ByteReader reader):
        self.player_id = reader.readByte(True)
        self.value = read_color(reader)
    
    cpdef write(self, ByteWriter reader):
        reader.writeByte(self.id, True)
        reader.writeByte(self.player_id, True)
        write_color(reader, self.value)

cdef class ExistingPlayer(Loader):
    id = id_iter.next()
    
    cdef public:
        int player_id, team, weapon, tool, kills
        unsigned int color
        object name
    
    cpdef read(self, ByteReader reader):
        self.player_id = reader.readByte(True)
        self.team = reader.readByte(False)
        self.weapon = reader.readByte(True)
        self.tool = reader.readByte(True)
        self.kills = reader.readInt(True, False)
        self.color = read_color(reader)
        self.name = decode(reader.readString()) # 16 bytes
    
    cpdef write(self, ByteWriter reader):
        reader.writeByte(self.id, True)
        reader.writeByte(self.player_id, True)
        reader.writeByte(self.team, False)
        reader.writeByte(self.weapon, True)
        reader.writeByte(self.tool, True)
        reader.writeInt(self.kills, True, False)
        write_color(reader, self.color)
        reader.writeString(encode(self.name))

cdef class ShortPlayerData(Loader):
    id = id_iter.next()
    
    cdef public:
        int player_id, team, weapon
    
    cpdef read(self, ByteReader reader):
        self.player_id = reader.readByte(True)
        self.team = reader.readByte(False)
        self.weapon = reader.readByte(True)
    
    cpdef write(self, ByteWriter reader):
        reader.writeByte(self.id, True)
        reader.writeByte(self.player_id, True)
        reader.writeByte(self.team, False)
        reader.writeByte(self.weapon, True)
    
cdef class MoveObject(Loader):
    id = id_iter.next()
    
    cdef public:
        unsigned int object_type, state
        float x, y, z
    
    cpdef read(self, ByteReader reader):
        self.object_type = reader.readByte(True)
        self.state = reader.readByte(True)
        self.x = reader.readFloat(False)
        self.y = reader.readFloat(False)
        self.z = reader.readFloat(False)
        
    cpdef write(self, ByteWriter reader):
        reader.writeByte(self.id, True)
        reader.writeByte(self.object_type, True)
        reader.writeByte(self.state, True)
        reader.writeFloat(self.x, False)
        reader.writeFloat(self.y, False)
        reader.writeFloat(self.z, False)

cdef class CreatePlayer(Loader):
    id = id_iter.next()
    
    cdef public:
        unsigned int player_id, weapon
        int team
        float x, y, z
        object name

    cpdef read(self, ByteReader reader):
        self.player_id = reader.readByte(True)
        self.weapon = reader.readByte(True)
        self.team = reader.readByte(False)
        read_position(reader, &self.x, &self.y, &self.z)
        self.name = decode(reader.readString())
    
    cpdef write(self, ByteWriter reader):
        reader.writeByte(self.id, True)
        reader.writeByte(self.player_id, True)
        reader.writeByte(self.weapon, True)
        reader.writeByte(self.team, False)
        write_position(reader, self.x, self.y, self.z)
        reader.writeString(encode(self.name))

cdef class BlockAction(Loader):
    id = id_iter.next()
    
    cdef public:
        int x, y, z, value, player_id

    cpdef read(self, ByteReader reader):
        self.player_id = reader.readByte(True)
        self.value = reader.readByte(True)
        self.x = reader.readInt(False, False)
        self.y = reader.readInt(False, False)
        self.z = reader.readInt(False, False)
    
    cpdef write(self, ByteWriter reader):
        reader.writeByte(self.id, True)
        reader.writeByte(self.player_id, True)
        reader.writeByte(self.value, True)
        reader.writeInt(self.x, False, False)
        reader.writeInt(self.y, False, False)
        reader.writeInt(self.z, False, False)

cdef class BlockLine(Loader):
    id = id_iter.next()
    
    cdef public:
        int player_id
        int x1, y1, z1
        int x2, y2, z2
    
    cpdef read(self, ByteReader reader):
        self.player_id = reader.readByte(True)
        self.x1 = reader.readInt(False, False)
        self.y1 = reader.readInt(False, False)
        self.z1 = reader.readInt(False, False)
        self.x2 = reader.readInt(False, False)
        self.y2 = reader.readInt(False, False)
        self.z2 = reader.readInt(False, False)
    
    cpdef write(self, ByteWriter reader):
        reader.writeByte(self.id, True)
        reader.writeByte(self.player_id, True)
        reader.writeInt(self.x1, False, False)
        reader.writeInt(self.y1, False, False)
        reader.writeInt(self.z1, False, False)
        reader.writeInt(self.x2, False, False)
        reader.writeInt(self.y2, False, False)
        reader.writeInt(self.z2, False, False)
        
cdef class CTFState(Loader):
    id = 0
    
    cdef public:
        unsigned int team1_score, team2_score, cap_limit
        bint team1_has_intel, team2_has_intel
        unsigned int team1_carrier, team2_carrier
        float team1_flag_x, team1_flag_y, team1_flag_z
        float team2_flag_x, team2_flag_y, team2_flag_z
        float team1_base_x, team1_base_y, team1_base_z
        float team2_base_x, team2_base_y, team2_base_z
    
    cpdef read(self, ByteReader reader):
        self.team1_score = reader.readByte(True)
        self.team2_score = reader.readByte(True)
        self.cap_limit = reader.readByte(True)

        cdef int intel_flags = reader.readByte(True)
        self.team1_has_intel = intel_flags & 1
        self.team2_has_intel = (intel_flags >> 1) & 1

        if self.team2_has_intel:
            self.team1_carrier = reader.readByte(True)
            reader.skipBytes(11)
        else:
            read_position(reader, &self.team1_flag_x, &self.team1_flag_y,
                &self.team1_flag_z)
        
        if self.team1_has_intel:
            self.team2_carrier = reader.readByte(True)
            reader.skipBytes(11)
        else:
            read_position(reader, &self.team2_flag_x, &self.team2_flag_y,
                &self.team2_flag_z)
        
        read_position(reader, &self.team1_base_x, &self.team1_base_y,
            &self.team1_base_z)

        read_position(reader, &self.team2_base_x, &self.team2_base_y,
            &self.team2_base_z)
    
    cpdef write(self, ByteWriter reader):
        reader.writeByte(self.team1_score, True)
        reader.writeByte(self.team2_score, True)
        reader.writeByte(self.cap_limit, True)
        cdef int intel_flags = (self.team1_has_intel | (
            self.team2_has_intel << 1))
            
        reader.writeByte(intel_flags, True)
        
        if self.team2_has_intel:
            reader.writeByte(self.team1_carrier, True)
            reader.pad(11)
        else:
            write_position(reader, self.team1_flag_x, self.team1_flag_y,
                self.team1_flag_z)
        
        if self.team1_has_intel:
            reader.writeByte(self.team2_carrier, True)
            reader.pad(11)
        else:
            write_position(reader, self.team2_flag_x, self.team2_flag_y,
                self.team2_flag_z)
        
        write_position(reader, self.team1_base_x, self.team1_base_y,
            self.team1_base_z)
        
        write_position(reader, self.team2_base_x, self.team2_base_y,
            self.team2_base_z)
            
DEF MAX_TERRITORIES = 16
DEF TERRITORY_SIZE = 4*3+1
DEF TERRITORY_DATA = MAX_TERRITORIES * TERRITORY_SIZE

cdef class Territory(Loader):
    cdef public:
        float x, y, z
        unsigned int state
    
    cpdef read(self, ByteReader reader):
        read_position(reader, &self.x, &self.y, &self.z)
        self.state = reader.readByte(True)
    
    cpdef write(self, ByteWriter reader):
        write_position(reader, self.x, self.y, self.z)
        reader.writeByte(self.state, True)

cdef class ObjectTerritory(Loader):
    cdef public:
        object item

    cpdef write(self, ByteWriter reader):
        write_position(reader, self.item.x, self.item.y, self.item.z)
        team = self.item.team
        cdef int state
        if team is None:
            state = NEUTRAL_TEAM
        else:
            state = team.id
        reader.writeByte(state, True)

cdef class TCState(Loader):
    id = 1
    
    cdef public:
        list territories
    
    cpdef read(self, ByteReader reader):
        self.territories = []
        cdef unsigned int count = reader.readByte(True)
        for _ in xrange(count):
            self.territories.append(Territory(reader))
    
    def set_entities(self, items):
        self.territories = []
        for item in items:
            territory = ObjectTerritory()
            territory.item = item
            self.territories.append(territory)
    
    cpdef write(self, ByteWriter reader):
        cdef Loader territory
        reader.writeByte(len(self.territories), True)
        for territory in self.territories:
            territory.write(reader)
        reader.pad((MAX_TERRITORIES - len(self.territories)) * TERRITORY_SIZE)
    
modes = {
    CTF_MODE : CTFState,
    TC_MODE : TCState
}

cdef inline tuple read_team_color(ByteReader reader):
    b = reader.readByte(True)
    g = reader.readByte(True)
    r = reader.readByte(True)
    return (r, g, b)

cdef inline void write_team_color(ByteWriter reader, tuple color):
    r, g, b = color
    reader.writeByte(b, True)
    reader.writeByte(g, True)
    reader.writeByte(r, True)

cdef class StateData(Loader):
    id = id_iter.next()
    
    cdef public:
        int player_id
        tuple fog_color
        tuple team1_color
        tuple team2_color
        Loader state
        object team1_name, team2_name

    cpdef read(self, ByteReader reader):
        self.player_id = reader.readByte(True)
        self.fog_color = read_team_color(reader)
        self.team1_color = read_team_color(reader)
        self.team2_color = read_team_color(reader)
        self.team1_name = decode(reader.readString(10))
        self.team2_name = decode(reader.readString(10))
        cdef int mode = reader.readByte(True)
        self.state = modes[mode](reader)
        
    cpdef write(self, ByteWriter reader):
        reader.writeByte(self.id, True)
        reader.writeByte(self.player_id, True)
        write_team_color(reader, self.fog_color)
        write_team_color(reader, self.team1_color)
        write_team_color(reader, self.team2_color)
        reader.writeString(encode(self.team1_name), 10)
        reader.writeString(encode(self.team2_name), 10)
        reader.writeByte(self.state.id, True)
        self.state.write(reader)

cdef class KillAction(Loader):
    id = id_iter.next()
    
    cdef public:
        int player_id, killer_id, kill_type, respawn_time
    
    cpdef read(self, ByteReader reader):
        self.player_id = reader.readByte(True)
        self.killer_id = reader.readByte(True)
        self.kill_type = reader.readByte(True)
        self.respawn_time = reader.readByte(True)
    
    cpdef write(self, ByteWriter reader):
        reader.writeByte(self.id, True)
        reader.writeByte(self.player_id, True)
        reader.writeByte(self.killer_id, True)
        reader.writeByte(self.kill_type, True)
        reader.writeByte(self.respawn_time, True)

cdef class ChatMessage(Loader):
    id = id_iter.next()

    cdef public:
        unsigned int player_id, chat_type
        object value
    
    cpdef read(self, ByteReader reader):
        self.player_id = reader.readByte(True)
        self.chat_type = reader.readByte(True)
        self.value = decode(reader.readString())
    
    cpdef write(self, ByteWriter reader):
        reader.writeByte(self.id, True)
        reader.writeByte(self.player_id, True)
        reader.writeByte(self.chat_type, True)
        reader.writeString(encode(self.value))

cdef class MapStart(Loader):
    id = id_iter.next()
    
    cdef public:
        unsigned int size
    
    cpdef read(self, ByteReader reader):
        self.size = reader.readInt(True, False)
    
    cpdef write(self, ByteWriter reader):
        reader.writeByte(self.id, True)
        reader.writeInt(self.size, True, False)

cdef class MapChunk(Loader):
    id = id_iter.next()
    
    cdef public:
        object data
    
    cpdef read(self, ByteReader reader):
        self.data = reader.read()
    
    cpdef write(self, ByteWriter reader):
        reader.writeByte(self.id, True)
        reader.write(self.data)

cdef class PlayerLeft(Loader):
    id = id_iter.next()
    
    cdef public:
        int player_id
    
    cpdef read(self, ByteReader reader):
        self.player_id = reader.readByte(True)
    
    cpdef write(self, ByteWriter reader):
        reader.writeByte(self.id, True)
        reader.writeByte(self.player_id, True)

cdef class TerritoryCapture(Loader):
    id = id_iter.next()
    
    cdef public:
        unsigned int object_index, winning, state
    
    cpdef read(self, ByteReader reader):
        self.object_index = reader.readByte(True)
        self.winning = reader.readByte(True)
        self.state = reader.readByte(True)
    
    cpdef write(self, ByteWriter reader):
        reader.writeByte(self.id, True)
        reader.writeByte(self.object_index, True)
        reader.writeByte(self.winning, True)
        reader.writeByte(self.state, True)

cdef class ProgressBar(Loader):
    id = id_iter.next()
    
    cdef public:
        unsigned int object_index, capturing_team
        int rate
        float progress
    
    cpdef read(self, ByteReader reader):
        self.object_index = reader.readByte(True)
        self.capturing_team = reader.readByte(True)
        self.rate = reader.readByte(False)
        self.progress = reader.readFloat(False)
    
    cpdef write(self, ByteWriter reader):
        reader.writeByte(self.id, True)
        reader.writeByte(self.object_index, True)
        reader.writeByte(self.capturing_team, True)
        reader.writeByte(self.rate, False)
        reader.writeFloat(self.progress, False)

cdef class IntelCapture(Loader):
    id = id_iter.next()
    
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
    id = id_iter.next()
    
    cdef public:
        int player_id
    
    cpdef read(self, ByteReader reader):
        self.player_id = reader.readByte(True)
    
    cpdef write(self, ByteWriter reader):
        reader.writeByte(self.id, True)
        reader.writeByte(self.player_id, True)

cdef class IntelDrop(Loader):
    id = id_iter.next()
    
    cdef public:
        int player_id
        float x, y, z
    
    cpdef read(self, ByteReader reader):
        self.player_id = reader.readByte(True)
        read_position(reader, &self.x, &self.y, &self.z)
    
    cpdef write(self, ByteWriter reader):
        reader.writeByte(self.id, True)
        reader.writeByte(self.player_id, True)
        write_position(reader, self.x, self.y, self.z)

cdef class Restock(Loader):
    id = id_iter.next()
    
    cdef public:
        int player_id
    
    cpdef read(self, ByteReader reader):
        self.player_id = reader.readByte(True)
    
    cpdef write(self, ByteWriter reader):
        reader.writeByte(self.id, True)
        reader.writeByte(self.player_id, True)

cdef class FogColor(Loader):
    id = id_iter.next()
    
    cdef public:
        int color
    
    cpdef read(self, ByteReader reader):
        self.color = reader.readInt(True, False) >> 8
    
    cpdef write(self, ByteWriter reader):
        reader.writeByte(self.id, True)
        reader.writeInt(self.color << 8, True, False)

cdef class WeaponReload(Loader):
    id = id_iter.next()
    
    cdef public:
        int player_id, clip_ammo, reserve_ammo
    
    cpdef read(self, ByteReader reader):
        self.player_id = reader.readByte(True)
        self.clip_ammo = reader.readByte(True)
        self.reserve_ammo = reader.readByte(True)
    
    cpdef write(self, ByteWriter reader):
        reader.writeByte(self.id, True)
        reader.writeByte(self.player_id, True)
        reader.writeByte(self.clip_ammo, True)
        reader.writeByte(self.reserve_ammo, True)

cdef class ChangeTeam(Loader):
    id = id_iter.next()
    
    cdef public:
        int player_id, team

    cpdef read(self, ByteReader reader):
        self.player_id = reader.readByte(True)
        self.team = reader.readByte(False)
    
    cpdef write(self, ByteWriter reader):
        reader.writeByte(self.id, True)
        reader.writeByte(self.player_id, True)
        reader.writeByte(self.team, False)

cdef class ChangeWeapon(Loader):
    id = id_iter.next()
    
    cdef public:
        int player_id, weapon

    cpdef read(self, ByteReader reader):
        self.player_id = reader.readByte(True)
        self.weapon = reader.readByte(True)
    
    cpdef write(self, ByteWriter reader):
        reader.writeByte(self.id, True)
        reader.writeByte(self.player_id, True)
        reader.writeByte(self.weapon, True)