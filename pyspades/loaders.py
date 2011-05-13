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
from pyspades import debug

class PacketLoader(object):
    id = None
    def __init__(self, reader = None):
        if reader is not None:
            self.read(reader)
    
    def read(self, reader):
        raise NotImplementedError('read() not implemented')

    def write(self, reader):
        raise NotImplementedError('write() not implemented')

class Ack(PacketLoader):
    unknown = None
    sequence2 = None
    timer = None
    def read(self, reader): # uses byte
        self.sequence2 = reader.readShort(True) # sequence number?
        self.timer = reader.readShort(True) # timer?

class ConnectionRequest(PacketLoader):
    auth_value = None
    version = None
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
        dword_7 = reader.readInt(True) # version
        
        check_default(word_1, 0)
        check_default(v10, -1)
        check_default(v12, -1)
        check_default(v16, 1400)
        check_default(v21, 32768)
        check_default(v2, 1)
        check_default(dword_1, 0)
        check_default(dword_2, 0)
        check_default(dword_3, 5000)
        check_default(dword_4, 2)
        check_default(dword_5, 2)
        self.auth_val = dword_6
        self.version = dword_7
        print 'version:', self.version

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

class Disconnect(PacketLoader):
    def read(self, reader):
        dword_1 = reader.readInt(True)
        check_default(dword_1, 0)

class Ping(PacketLoader):
    def read(self, reader):
        pass # uses both sequence and byte

class UserInput(PacketLoader):
    def read(self, reader): # uses byte
        size = reader.readShort(True)
        new_data = reader.readReader(size)
        type = new_data.readByte(True)

class Packet7(PacketLoader):
    def read(self, reader): # uses byte
        reader.skipBytes(2)
        size = reader.readShort(True)
        new_data = reader.readReader(size)

class Packet8(PacketLoader):
    def read(self, reader): # uses both
        reader.skipBytes(2)
        size = reader.readShort(True)
        v27 = reader.readInt(True)
        v28 = reader.readInt(True)
        v14 = reader.readInt(True)
        v16 = reader.readInt(True)
        new_data = reader.readReader(size)

class Packet9(PacketLoader):
    def read(self, reader): # uses byte
        word_1 = reader.readShort(True)
        size = reader.readShort(True)
        new_data = reader.readReader(size)

class Packet10(PacketLoader):
    def read(self, reader): # 
        dword_1 = reader.readInt(True)
        dword_2 = reader.readInt(True)

class Packet11(PacketLoader):
    def read(self, reader):
        dword_1 = reader.readInt(True)
        dword_2 = reader.readInt(True)
        dword_3 = reader.readInt(True)