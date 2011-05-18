from pyspades.common import *
from pyspades.loaders import PacketLoader

class _InformationCommon(PacketLoader):
    x = None
    y = None
    z = None
    def read(self, reader):
        reader.skipBytes(1)
        self.x = reader.readFloat(False) # x
        self.y = reader.readFloat(False) # y
        self.z = reader.readFloat(False) # z
    
    def write(self, reader):
        reader.writeByte(self.id)
        reader.writeFloat(self.x)
        reader.writeFloat(self.y)
        reader.writeFloat(self.z)

class PositionData(_InformationCommon):
    pass

class OrientationData(_InformationCommon):
    pass

class MovementData(PacketLoader):
    up = None
    down = None
    left = None
    right = None
    def read(self, reader):
        firstByte = reader.readByte(True)
        self.up = (firstByte >> 4) & 1 # going forward?
        self.down = (firstByte >> 5) & 1 # going back?
        self.left = (firstByte >> 6) & 1 # going left?
        self.right = (firstByte >> 7) # going right?
    
    def write(self, reader):
        up = int(self.up)
        down = int(self.down)
        left = int(self.left)
        right = int(self.right)
        byte = self.id | (up << 4) | (down << 5) | (left << 6) | (right << 7)
        reader.writeByte(byte, True)

class AnimationData(PacketLoader):
    fire = None
    jump = None
    crouch = None
    aim = None
    def read(self, reader):
        firstByte = reader.readByte(True)
        self.fire = (firstByte >> 4) & 1
        self.jump = (firstByte >> 5) & 1
        self.crouch = (firstByte >> 6) & 1
        self.aim = (firstByte >> 7)
    
    def write(self, reader):
        fire = int(self.fire)
        jump = int(self.jump)
        crouch = int(self.crouch)
        aim = int(self.aim)
        byte = self.id | (fire << 4) | (jump << 5) | (crouch << 6) | (aim << 7)
        reader.writeByte(byte, True)

class HitPacket(PacketLoader):
    player_id = None
    value = None
    def read(self, reader):
        firstByte = reader.readByte(True)
        byte = reader.readByte(True)
        if firstByte & 0x10:
            self.value = byte
            self.player_id = None
        else:
            self.value = firstByte >> 5
            self.player_id = byte
    
    def write(self, reader):
        byte = self.id
        if self.player_id is None:
            byte |= 0x10
            reader.writeByte(byte, True)
            reader.writeByte(self.value)
        else:
            byte |= self.value << 5
            reader.writeByte(byte, True)
            reader.writeByte(self.player_id)

class GrenadePacket(PacketLoader):
    value = None
    def read(self, reader):
        reader.skipBytes(1)
        self.value = reader.readFloat(False)
    
    def write(self, reader):
        reader.writeByte(self.id)
        reader.writeFloat(self.value, False)

class SetWeapon(PacketLoader):
    value = None
    def read(self, reader):
        firstByte = reader.readByte(True)
        self.value = firstByte >> 4 # tool
        # 0 -> spade, 1 -> dagger, 2 -> block, 3 -> gun
    
    def write(self, reader):
        byte = self.id
        byte |= self.value << 4
        reader.writeByte(byte, True)

class SetColor(PacketLoader):
    def read(self, reader):
        firstInt = reader.readInt(True, False)
        self.value = firstInt >> 4
    
    def write(self, reader):
        value = self.id
        value |= self.value << 4
        reader.writeInt(value, True, False)

class JoinTeam(PacketLoader):
    name = None
    team = None
    def read(self, reader):
        firstByte = reader.readByte(True)
        self.team = firstByte >> 4 # 0 for b, 1 for g
        firstInt = reader.readInt(True, False)
        check_default(firstInt, 594641620)
        self.name = reader.readString()
    
    def write(self, reader):
        byte = self.id
        byte |= self.team << 4
        reader.writeByte(byte, True)
        reader.writeInt(594641620, True, False)
        reader.writeString(self.name)

class BlockAction(PacketLoader):
    x = y = z = None
    value = None
    def read(self, reader):
        firstInt = reader.readInt(True, False)
        self.x = (firstInt >> 6) & 0x1FF # x
        self.y = (firstInt >> 15) & 0x1FF # y
        self.z = (firstInt >> 24) & 0x3F # z
        # 0 -> build, 1 -> destroy, 2 -> spade destroy, 3 -> grenade destroy
        self.value = (firstInt >> 4) & 3
    
    def write(self, reader):
        value = (self.id | (self.x << 6) | (self.y << 15) | (self.z << 24) |
            (self.value << 4))
        reader.writeInt(value, True, False)

class KillAction(PacketLoader):
    player_id = None
    
    def read(self, reader):
        reader.skipBytes(1)
        self.player_id = reader.readByte(True)
    
    def write(self, reader):
        reader.writeByte(self.id)
        reader.writeByte(self.player_id)

class ChatMessage(PacketLoader):
    global_message = None
    value = None
    
    def read(self, reader):
        firstByte = reader.readByte(True)
        self.global_message = (firstByte & 0xF0) != 32
        self.value = reader.readString()
    
    def write(self, reader):
        byte = self.id
        if self.global_message:
            byte |= 16
        else:
            byte |= 32
        reader.writeByte(byte, True)
        reader.writeString(self.value)