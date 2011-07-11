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
        float x, y, z

    cpdef read(self, ByteReader reader):
        reader.skipBytes(1)
        self.x = reader.readFloat(False) # x
        self.y = reader.readFloat(False) # y
        self.z = reader.readFloat(False) # z
    
    cpdef write(self, ByteWriter reader):
        reader.writeByte(self.id, True)
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
        bint up, down, left, right
    
    cpdef read(self, ByteReader reader):
        cdef int firstByte = reader.readByte(True)
        self.up = (firstByte >> 4) & 1 # going forward?
        self.down = (firstByte >> 5) & 1 # going back?
        self.left = (firstByte >> 6) & 1 # going left?
        self.right = (firstByte >> 7) # going right?
    
    cpdef write(self, ByteWriter reader):
        cdef int up = self.up
        cdef int down = self.down
        cdef int left = self.left
        cdef int right = self.right
        cdef int byte
        byte = self.id | (up << 4) | (down << 5) | (left << 6) | (right << 7)
        reader.writeByte(byte, True)

cdef class AnimationData(Loader):
    id = 3

    cdef public:
        bint fire, jump, crouch, aim

    cpdef read(self, ByteReader reader):
        cdef int firstByte = reader.readByte(True)
        self.fire = (firstByte >> 4) & 1
        self.jump = (firstByte >> 5) & 1
        self.crouch = (firstByte >> 6) & 1
        self.aim = (firstByte >> 7)
    
    cpdef write(self, ByteWriter reader):
        cdef int fire = self.fire
        cdef int jump = self.jump
        cdef int crouch = self.crouch
        cdef int aim = self.aim
        cdef int byte
        byte = self.id | (fire << 4) | (jump << 5) | (crouch << 6) | (aim << 7)
        reader.writeByte(byte, True)

cdef class HitPacket(Loader):
    id = 4
    
    cdef public:
        int player_id, value
    
    cpdef read(self, ByteReader reader):
        cdef int firstByte = reader.readByte(True)
        cdef int byte = reader.readByte(True)
        self.value = firstByte >> 4
        self.player_id = byte
    
    cpdef write(self, ByteWriter reader):
        cdef int byte = self.id
        byte |= self.value << 4
        reader.writeByte(byte, True)
        reader.writeByte(self.player_id, True)

cdef class GrenadePacket(Loader):
    id = 5

    cdef public:
        float value

    cpdef read(self, ByteReader reader):
        reader.skipBytes(1)
        self.value = reader.readFloat(False)
    
    cpdef write(self, ByteWriter reader):
        reader.writeByte(self.id, True)
        reader.writeFloat(self.value, False)

cdef class SetTool(Loader):
    id = 6
    cdef public:
        int value

    cpdef read(self, ByteReader reader):
        cdef int firstByte = reader.readByte(True)
        self.value = firstByte >> 4 # tool
        # 0 -> spade, 1 -> dagger, 2 -> block, 3 -> gun
    
    cpdef write(self, ByteWriter reader):
        cdef int byte = self.id
        byte |= self.value << 4
        reader.writeByte(byte, True)

cdef class SetColor(Loader):
    id = 7
    
    cdef public:
        unsigned int value
    
    cpdef read(self, ByteReader reader):
        cdef unsigned int firstInt = reader.readInt(True, False)
        self.value = firstInt >> 4
    
    cpdef write(self, ByteWriter reader):
        cdef unsigned int value = self.id
        value |= self.value << 4
        reader.writeInt(value, True, False)

cdef class JoinTeam(Loader):
    id = 8
    
    cdef public:
        object name
        int team
        int weapon
    
    cpdef read(self, ByteReader reader):
        # respawn?
        cdef int firstByte = reader.readByte(True)
        cdef int selector = (firstByte >> 4) & 1
        cdef int value = (firstByte >> 5)
        if reader.dataLeft():
            self.name = decode(reader.readString())
            self.team = selector
            self.weapon = value
        elif selector == 0:
            self.team = value
            self.weapon = -1
        else:
            self.team = -1
            self.weapon = value
    
    cpdef write(self, ByteWriter reader):
        cdef int byte = self.id
        if self.name is not None:
            byte |= self.team << 4
            byte |= self.weapon << 5
        elif self.team != -1:
            byte |= self.team << 5
        else:
            byte |= 1 << 4
            byte |= self.weapon << 5
        reader.writeByte(byte, True)
        if self.name is not None:
            reader.writeString(encode(self.name))

cdef class BlockAction(Loader):
    id = 11
    
    cdef public:
        int x, y, z, value

    cpdef read(self, ByteReader reader):
        cdef unsigned int firstInt = reader.readInt(True, False)
        self.x = (firstInt >> 6) & 0x1FF # x
        self.y = (firstInt >> 15) & 0x1FF # y
        self.z = (firstInt >> 24) & 0x3F # z
        # 0 -> build, 1 -> destroy, 2 -> spade destroy, 3 -> grenade destroy
        self.value = (firstInt >> 4) & 3
    
    cpdef write(self, ByteWriter reader):
        cdef unsigned int value
        value = (self.id | (self.x << 6) | (self.y << 15) | (self.z << 24) |
            (self.value << 4))
        reader.writeInt(value, True, False)

cdef class ChatMessage(Loader):
    id = 14
    cdef public:
        bint global_message
        object value
    
    cpdef read(self, ByteReader reader):
        cdef int firstByte = reader.readByte(True)
        self.global_message = (firstByte & 0xF0) != 32
        self.value = decode(reader.readString())
    
    cpdef write(self, ByteWriter reader):
        cdef int byte = self.id
        if self.global_message:
            byte |= 16
        else:
            byte |= 32
        reader.writeByte(byte, True)
        reader.writeString(encode(self.value))