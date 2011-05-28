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
from pyspades.bytereader import ByteReader
from pyspades import debug

class PacketLoader(object):
    id = None
    ack = None
    byte = None
    sequence = None
    def __init__(self, reader = None):
        if reader is not None:
            self.read(reader)
    
    def read(self, reader):
        raise NotImplementedError('read() not implemented')

    def write(self, reader):
        raise NotImplementedError('write() not implemented')
    
    def generate(self):
        reader = ByteReader()
        self.write(reader)
        return reader

class Ack(PacketLoader):
    sequence2 = None
    timer = None
    def read(self, reader): # uses byte
        self.sequence2 = reader.readShort(True) # sequence number?
        self.timer = reader.readShort(True) # timer?
    
    def write(self, reader):
        reader.writeShort(self.sequence2, True)
        reader.writeShort(self.timer, True)

class ConnectionRequest(PacketLoader):
    auth_value = None
    version = None
    client = True
    value = None
    def read(self, reader):
        word_1 = reader.readShort(True)
        v10 = reader.readByte()
        v12 = reader.readByte()
        v16 = reader.readInt(True)
        v21 = reader.readInt(True)
        v2 = reader.readInt(True)
        dword_1 = reader.readInt(True)
        dword_2 = reader.readInt(True)
        dword_3 = reader.readInt(True)
        dword_4 = reader.readInt(True)
        dword_5 = reader.readInt(True)
        # server responds with this in packet 3
        dword_6 = reader.readInt(True, False)
        dword_7 = reader.readInt(True, False) # version, CRC32 of exe
        
        if word_1 not in (0, 1):
            raw_input('unknown word_1: %s' % word_1)
        if v10 == -1 and v12 == -1:
            self.client = True
        elif v10 != v12:
            raw_input('unknown v10 and v12: %s %s' % (v10, v12))
        else:
            self.client = False
            self.value = v10
        check_default(v16, 1400)
        check_default(v21, 32768)
        check_default(v2, 1)
        if dword_1 not in (0, 0x80000):
            raw_input('unknown dword_1: %s' % dword_1)
        check_default(dword_2, 0)
        check_default(dword_3, 5000)
        check_default(dword_4, 2)
        check_default(dword_5, 2)
        self.auth_val = dword_6
        self.version = dword_7
    
    def write(self, reader):
        reader.writeShort(0)
        if self.client:
            value = -1
        else:
            value = self.value or 0
        for _ in xrange(2):
            reader.writeByte(value)
        reader.writeInt(1400)
        reader.writeInt(32768)
        reader.writeInt(1)
        reader.writeInt(0)
        reader.writeInt(0)
        reader.writeInt(5000)
        reader.writeInt(2)
        reader.writeInt(2)
        reader.writeInt(self.auth_val, True, False)
        reader.writeInt(self.version, True, False)

class ConnectionResponse(PacketLoader):
    connection_id = None
    unique = None
    auth_val = None
    def read(self, reader):
        word_1 = reader.readShort(True)
        byte_1 = reader.readByte(True)
        byte_2 = reader.readByte(True)
        dword_1 = reader.readInt(True)
        dword_2 = reader.readInt(True)
        dword_3 = reader.readInt(True)
        dword_4 = reader.readInt(True)
        dword_5 = reader.readInt(True)
        dword_6 = reader.readInt(True)
        dword_7 = reader.readInt(True)
        dword_8 = reader.readInt(True)
        # server sent this in 
        dword_9 = reader.readInt(True, False)
        
        self.connection_id = word_1
        if byte_1 != byte_2:
            raise NotImplementedError('uniques not equal')
        self.unique = byte_1
        check_default(dword_1, 91750400)
        check_default(dword_2, 32768)
        check_default(dword_3, 1)
        check_default(dword_4, 0)
        check_default(dword_5, 0)
        check_default(dword_6, 5000)
        check_default(dword_7, 2)
        check_default(dword_8, 2)
        
        self.auth_val = dword_9
    
    def write(self, reader):
        reader.writeShort(self.connection_id, True)
        reader.writeByte(self.unique, True)
        reader.writeByte(self.unique, True)
        reader.writeInt(91750400, True)
        reader.writeInt(32768, True)
        reader.writeInt(1, True)
        reader.writeInt(0, True)
        reader.writeInt(0, True)
        reader.writeInt(5000, True)
        reader.writeInt(2, True)
        reader.writeInt(2, True)
        reader.writeInt(self.auth_val, True, False)

class Disconnect(PacketLoader):
    def read(self, reader):
        dword_1 = reader.readInt(True)
        check_default(dword_1, 0)
    
    def write(self, reader):
        reader.writeInt(0)

class Ping(PacketLoader):
    def read(self, reader):
        pass
        # uses both sequence and byte
    
    def write(self, reader):
        pass

class SizedData(PacketLoader):
    input_type = None
    data = None
    def read(self, reader): # uses byte
        size = reader.readShort(True)
        data = reader.readReader(size)
        self.data = data
    
    def write(self, reader):
        reader.writeShort(len(self.data))
        reader.write(str(self.data))

class Packet7(PacketLoader):
    def read(self, reader): # uses byte
        reader.skipBytes(2)
        size = reader.readShort(True)
        new_data = reader.readReader(size)

class MapData(PacketLoader):
    sequence2 = None
    total_num = None
    num = None
    data_size = None
    current_pos = None
    data = None
    def read(self, reader): # uses both
        self.sequence2 = reader.readShort(True) # seq at which this was sent at
        size = reader.readShort(True)
        self.total_num = reader.readInt(True) # total num
        self.num = reader.readInt(True) # packet num?
        self.data_size = reader.readInt(True) # total
        self.current_pos = reader.readInt(True) # current pos
        self.data = reader.readReader(size)
        
    def write(self, reader):
        reader.writeShort(self.sequence2, True)
        reader.writeShort(len(self.data), True)
        reader.writeInt(self.total_num, True)
        reader.writeInt(self.num, True)
        reader.writeInt(self.data_size, True)
        reader.writeInt(self.current_pos, True)
        reader.write(str(self.data))

class SizedSequenceData(PacketLoader):
    def read(self, reader): # uses byte
        self.sequence2 = reader.readShort(True) # sequence?
        size = reader.readShort(True)
        self.data = reader.readReader(size)
    
    def write(self, reader):
        reader.writeShort(self.sequence2, True)
        reader.writeShort(len(self.data))
        reader.write(str(self.data))

class Packet10(PacketLoader):
    dword_1 = None
    dword_2 = None
    def read(self, reader):
        self.dword_1 = reader.readInt(True)
        self.dword_2 = reader.readInt(True)
        check_default(self.dword_1, 0)
        check_default(self.dword_2, 0)
    
    def write(self, reader):
        reader.writeInt(self.dword_1 or 0, True)
        reader.writeInt(self.dword_2 or 0, True)

class Packet11(PacketLoader):
    def read(self, reader):
        self.dword_1 = reader.readInt(True)
        self.dword_2 = reader.readInt(True)
        self.dword_3 = reader.readInt(True)
        print 'PACKET 11:', self.dword_1, self.dword_2, self.dword_3
        raw_input()
    
    def write(self, reader):
        reader.writeInt(self.dword_1, True)
        reader.writeInt(self.dword_2, True)
        reader.writeInt(self.dword_3, True)

__all__ = ['Ack', 'ConnectionRequest', 'ConnectionResponse', 'Disconnect',
    'Ping', 'SizedData', 'Packet7', 'MapData', 'SizedSequenceData', 'Packet10',
    'Packet11']