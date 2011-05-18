from pyspades.common import *
from pyspades.loaders import PacketLoader

class _InformationCommon(PacketLoader):
    x = None
    y = None
    z = None
    player_id = None
    def read(self, reader):
        reader.skipBytes(1)
        self.player_id = reader.readByte(True)
        self.x = reader.readFloat(False) # x
        self.y = reader.readFloat(False) # y
        self.z = reader.readFloat(False) # z
    
    def write(self, reader):
        reader.writeByte(self.id, True)
        reader.writeByte(self.player_id)
        reader.writeFloat(self.x, False)
        reader.writeFloat(self.y, False)
        reader.writeFloat(self.z, False)

class PositionData(_InformationCommon):
    pass

class OrientationData(_InformationCommon):
    pass

class MovementData(PacketLoader):
    up = None
    down = None
    left = None
    right = None
    player_id = None
    def read(self, reader):
        firstByte = reader.readByte(True)
        self.player_id = reader.readByte(True)
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
        reader.writeByte(self.player_id, True)

class AnimationData(PacketLoader):
    fire = None
    jump = None
    crouch = None
    aim = None
    def read(self, reader):
        firstByte = reader.readByte(True)
        self.player_id = reader.readByte(True)
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
        reader.writeByte(self.player_id, True)

class HitPacket(PacketLoader):
    value = None
    def read(self, reader):
        firstByte = reader.readByte(True)
        self.value = firstByte >> 5
    
    def write(self, reader):
        byte = self.id
        byte |= (self.value << 5)
        reader.writeByte(byte, True)

class GrenadePacket(PacketLoader):
    value = None
    def read(self, reader):
        reader.skipBytes(1)
        self.player_id = reader.readByte(True)
        self.value = reader.readFloat(False)
    
    def write(self, reader):
        reader.writeByte(self.id)
        reader.writeByte(self.player_id, True)
        reader.writeFloat(self.value, False)

class SetWeapon(PacketLoader):
    value = None
    player_id = None
    def read(self, reader):
        firstByte = reader.readByte(True)
        self.player_id = reader.readByte(True)
        self.value = firstByte >> 4 # tool
        # 0 -> spade, 1 -> dagger, 2 -> block, 3 -> gun
    
    def write(self, reader):
        byte = self.id
        byte |= self.value << 4
        reader.writeByte(byte, True)
        reader.writeByte(self.player_id, True)

class SetColor(PacketLoader):
    value = None
    player_id = None
    def read(self, reader):
        firstInt = reader.readInt(True, False)
        self.player_id = reader.readByte(True)
        self.value = firstInt >> 4
    
    def write(self, reader):
        value = self.id
        value |= self.value << 4
        reader.writeInt(value, True, False)
        reader.writeByte(self.player_id, True)

class ExistingPlayer(PacketLoader):
    player_id = None
    team = None
    something = None
    kills = None
    color = None
    name = None
    
    def read(self, reader):
        firstInt = reader.readInt(True, False)
        self.player_id = (firstInt >> 4) & 0x1F
        self.team = (firstInt >> 9) & 9 # team
        self.something = (firstInt >> 10) & 7 # something?
        self.kills = (firstInt >> 13) & 0x7FF # kills
        reader.rewind(1)
        byte1 = reader.readByte(True)
        byte2 = reader.readByte(True)
        byte3 = reader.readByte(True)
        self.color = byte1 | ((byte2 | (byte3 << 8)) << 8) # color
        self.name = reader.readString()
    
    def write(self, reader):
        value = self.id
        value |= self.player_id << 4
        value |= self.team << 9
        value |= (self.something or 0) << 10
        value |= self.kills << 13
        byte1 = self.color & 0xFF
        byte2 = self.color & 0xFF00
        byte3 = self.color & 0xFF0000
        reader.writeInt(value, True, False)
        reader.rewind(1)
        reader.writeByte(byte1, True)
        reader.writeByte(byte2, True)
        reader.writeByte(byte3, True)
        reader.writeString(self.name)

class IntelAction(PacketLoader):
    player_id = None
    action_type = None
    x = None
    y = None
    z = None
    something1 = None
    something2 = None
    def read(self, reader):
        firstByte = reader.readByte(True)
        self.action_type = action_type = (firstByte >> 4) & 7
        if action_type == 0:
            byte = reader.readByte(True)
            self.something1 = byte & 3
            self.something2 = byte >> 2
            print '9:', action_type, something2, something3
        elif action_type == 1:
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
            self.x = (firstInt >> 12) & 0x1FF # x?
            self.y = firstInt >> 21 # y?
            self.z = reader.readByte(True) # z?
        
    def write(self, reader):
        value = self.id | (self.action_type << 4)
        if self.action_type == 0:
            reader.writeByte(value, True)
            byte = self.something1 | (self.something2 << 2)
            reader.writeByte(byte, True)
        elif self.action_type == 1:
            reader.writeByte(value, True)
            reader.writeByte(self.player_id, True)
        elif self.action_type in (2, 3):
            value |= self.player_id << 7
            value |= self.x << 12
            value |= self.y << 21
            reader.writeInt(value, True, False)
            reader.writeByte(self.z, True)

class CreatePlayer(PacketLoader):
    player_id = None
    name = None
    x = y = z = None
    def read(self, reader):
        # new player + spawn player
        firstInt = reader.readInt(True, False)
        self.name = reader.readString()
        self.player_id = (firstInt >> 4) & 31
        self.x = (firstInt >> 9) & 0x1FF
        self.y = (firstInt >> 18) & 0xFF
        self.z = (firstInt >> 26) & 0x3F
    
    def write(self, reader):
        value = self.id
        value |= self.player_id << 4
        value |= self.x << 9
        value |= self.y << 18
        value |= self.z << 26
        reader.writeInt(value, True, False)
        reader.writeString(self.name)

class BlockAction(PacketLoader):
    x = y = z = None
    value = None
    player_id = None
    def read(self, reader):
        firstInt = reader.readInt(True, False)
        self.x = (firstInt >> 6) & 0x1FF # x
        self.y = (firstInt >> 15) & 0x1FF # y
        self.z = (firstInt >> 24) & 0x3F # z
        # 0 -> build, 1 -> destroy, 2 -> spade destroy, 3 -> grenade destroy
        self.value = (firstInt >> 4) & 3
        if self.value == 0:
            self.player_id = reader.readByte(True)
    
    def write(self, reader):
        value = (self.id | (self.x << 6) | (self.y << 15) | (self.z << 24) |
            (self.value << 4))
        reader.writeInt(value, True, False)
        if self.value == 0:
            reader.writeByte(self.player_id, True)

def make_coordinate_bytes(x, y, z):
    byte1 = x & 0xFF
    byte2 = (x >> 8) | ((y << 1) & 0xFF)
    byte3 = (y >> 7) | (z << 2)
    return byte1, byte2, byte3

class PlayerData(PacketLoader):
    player_left = None

    blue_base_x = None
    blue_base_y = None
    blue_base_z = None
    
    green_base_x = None
    green_base_y = None
    green_base_z = None
    
    blue_flag_player = None
    blue_flag_x = None
    blue_flag_y = None
    blue_flag_z = None
    
    green_flag_player = None
    green_flag_x = None
    green_flag_y = None
    green_flag_z = None
    def read(self, reader):
        firstByte = reader.readByte(True)
        if firstByte & 16: # player left
            self.player_left = reader.readByte(1)
        else:
            reader.rewind(1)
            # initial reader
            firstInt = reader.readInt(True, False)
            self.count = (firstInt >> 5) & 0x1F # number of players?
            self.blue_score = (firstInt >> 10) & 0x3FF # team score 1?
            self.green_score = (firstInt >> 20) & 0x3FF # team score 2?
            if firstInt & 0x40000000:
                self.blue_flag_player = reader.readByte(True)
                reader.skipBytes(2)
            else:
                byte = reader.readByte(True)
                byte2 = reader.readByte(True)
                byte3 = reader.readByte(True)
                self.blue_flag_x = byte | ((byte2 & 1) << 8)
                self.blue_flag_y = (byte2 >> 1) | ((byte3 & 3) << 7)
                self.blue_flag_z = byte3 >> 2
            if (firstByte >> 31) & 1:
                self.green_flag_player = reader.readByte(True)
                reader.skipBytes(2)
            else:
                byte4 = reader.readByte(True)
                byte5 = reader.readByte(True)
                byte6 = reader.readByte(True)
                self.green_flag_x = byte4 | ((byte5 & 1) << 8)
                self.green_flag_y = (byte5 >> 1) | ((byte6 & 3) << 7)
                self.green_flag_z = byte6 >> 2
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
        
    def write(self, reader):
        value = self.id
        if self.player_left is not None:
            value |= 16
            reader.writeByte(value, True)
            reader.writeByte(self.player_left, True)
        else:
            value |= (self.count << 5)
            value |= (self.blue_score << 10)
            value |= (self.green_score << 20)
            if self.blue_flag_player is not None:
                value |= 0x40000000
            if self.green_flag_player is not None:
                value |= 0x80000000
            reader.writeInt(value, True, False)
            if self.blue_flag_player is not None:
                reader.writeByte(self.blue_flag_player, True)
                reader.writeByte(0)
                reader.writeByte(0)
            else:
                a, b, c = make_coordinate_bytes(self.blue_flag_x,
                    self.blue_flag_y, self.blue_flag_z)
                reader.writeByte(a, True)
                reader.writeByte(b, True)
                reader.writeByte(c, True)
            if self.green_flag_player is not None:
                a, b, c = make_coordinate_bytes(self.green_flag_x,
                    self.green_flag_y, self.green_flag_z)
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

class KillAction(PacketLoader):
    player1 = player2 = None
    
    def read(self, reader):
        firstShort = reader.readShort(True, False)
        self.player1 = (firstShort >> 4) & 31
        self.player2 = (firstShort >> 9) & 31
    
    def write(self, reader):
        value = self.id
        value |= self.player1 << 4
        value |= self.player2 << 9
        reader.writeShort(value, True, False)

class ChatMessage(PacketLoader):
    global_message = None
    value = None
    player_id = None
    
    def read(self, reader):
        firstByte = reader.readByte(True)
        self.player_id = reader.readByte(True)
        self.global_message = (firstByte & 0xF0) != 32
        self.value = reader.readString()
    
    def write(self, reader):
        byte = self.id
        if self.global_message:
            byte |= 16
        else:
            byte |= 32
        reader.writeByte(byte, True)
        reader.writeByte(self.player_id)
        reader.writeString(self.value)