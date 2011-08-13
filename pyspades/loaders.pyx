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
from pyspades.common cimport check_default_int
from pyspades import debug

cdef class Loader:
    def __init__(self, ByteReader reader = None):
        if reader is not None:
            self.read(reader)
    
    cpdef read(self, ByteReader reader):
        read_python = getattr(self, 'read', None)
        if read_python is None:
            raise NotImplementedError('read() not implemented')
        read_python(reader)

    cpdef write(self, ByteWriter reader):
        write_python = getattr(self, 'write', None)
        if read_python is None:
            raise NotImplementedError('write() not implemented')
        write_python(reader)
    
    cpdef ByteWriter generate(self):
        cdef ByteWriter reader = ByteWriter()
        self.write(reader)
        return reader

cdef class PacketLoader(Loader):
    pass

cdef class Packet0(PacketLoader):
    id = 0
    cpdef read(self, ByteReader reader):
        return

    cpdef write(self, ByteWriter reader):
        pass

cdef class Ack(PacketLoader):
    id = 1
    cdef public:
        int sequence2, timer
        
    cpdef read(self, ByteReader reader): # uses byte
        self.sequence2 = reader.readShort(True) # sequence number?
        self.timer = reader.readShort(True) # timer?
    
    cpdef write(self, ByteWriter reader):
        reader.writeShort(self.sequence2, True)
        reader.writeShort(self.timer, True)

cdef class ConnectionRequest(PacketLoader):
    id = 2
    cdef public:
        int value, value2
        unsigned int auth_val, version
        bint client

    cpdef read(self, ByteReader reader):
        cdef int outgoing_peer_id = reader.readShort(True)
        cdef int incoming_session_id = reader.readByte() # incoming session id
        cdef int outgoing_session_id = reader.readByte() # outgoing session id
        cdef unsigned int mtu = reader.readInt(True)
        cdef unsigned int window_size = reader.readInt(True)
        cdef unsigned int channel_count = reader.readInt(True)
        cdef unsigned int incoming_bandwidth = reader.readInt(True)
        cdef unsigned int outgoing_bandwidth = reader.readInt(True)
        cdef unsigned int throttle_interval = reader.readInt(True)
        cdef unsigned int throttle_acceleration = reader.readInt(True)
        cdef unsigned int throttle_deceleration = reader.readInt(True)
        # server responds with this in packet 3
        cdef unsigned int connect_id = reader.readInt(True, False)
        # version, CRC32 of exe
        cdef unsigned int data = reader.readInt(True, False)

        if incoming_session_id == -1 and outgoing_session_id == -1:
            self.client = True
        else:
            self.client = False
            self.value = incoming_session_id
        check_default_int(mtu, 1400)
        check_default_int(window_size, 32768)
        check_default_int(channel_count, 1)
        check_default_int(outgoing_bandwidth, 0)
        check_default_int(throttle_interval, 5000)
        check_default_int(throttle_acceleration, 2)
        check_default_int(throttle_deceleration, 2)
        self.auth_val = connect_id
        self.version = data
        self.value2 = outgoing_peer_id
    
    cpdef write(self, ByteWriter reader):
        reader.writeShort(self.value2)
        cdef int value
        if self.client:
            value = -1
        else:
            value = self.value or 0
        reader.writeByte(value)
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

cdef class ConnectionResponse(PacketLoader):
    id = 3
    cdef public:
        int connection_id, unique
        unsigned int auth_val

    cpdef read(self, ByteReader reader):
        cdef int outgoing_peer_id = reader.readShort(True)
        cdef int incoming_session_id = reader.readByte(True)
        cdef int outgoing_session_id = reader.readByte(True)
        cdef unsigned int mtu = reader.readInt(True)
        cdef unsigned int window_size = reader.readInt(True)
        cdef unsigned int channel_count = reader.readInt(True)
        cdef unsigned int incoming_bandwidth = reader.readInt(True)
        cdef unsigned int outgoing_bandwidth = reader.readInt(True)
        cdef unsigned int throttle_interval = reader.readInt(True)
        cdef unsigned int throttle_acceleration = reader.readInt(True)
        cdef unsigned int throttle_deceleration = reader.readInt(True)
        # server sent this in 
        cdef unsigned int connect_id = reader.readInt(True, False)
        
        self.connection_id = outgoing_peer_id
        self.unique = incoming_session_id
        check_default_int(mtu, 91750400)
        check_default_int(window_size, 32768)
        check_default_int(channel_count, 1)
        check_default_int(incoming_bandwidth, 0)
        check_default_int(outgoing_bandwidth, 0)
        check_default_int(throttle_interval, 5000)
        check_default_int(throttle_acceleration, 2)
        check_default_int(throttle_deceleration, 2)
        
        self.auth_val = connect_id
    
    cpdef write(self, ByteWriter reader):
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

cdef class Disconnect(PacketLoader):
    id = 4
    cpdef read(self, ByteReader reader):
        cdef unsigned int dword_1 = reader.readInt(True)
        check_default_int(dword_1, 0)
    
    cpdef write(self, ByteWriter reader):
        reader.writeInt(0)

cdef class Ping(PacketLoader):
    id = 5
    cpdef read(self, ByteReader reader):
        pass
        # uses both sequence and byte
    
    cpdef write(self, ByteWriter reader):
        pass

cdef class SizedData(PacketLoader):
    id = 6
    cdef public:
        object data
        
    cpdef read(self, ByteReader reader): # uses byte
        size = reader.readShort(True)
        self.data = reader.readReader(size)
    
    cpdef write(self, ByteWriter reader):
        reader.writeShort(len(self.data))
        reader.write(str(self.data))

cdef class Packet7(PacketLoader):
    id = 7

    cpdef read(self, ByteReader reader): # uses byte
        reader.skipBytes(2)
        cdef int size = reader.readShort(True)
        new_data = reader.readReader(size)

cdef class MapData(PacketLoader):
    id = 8
    
    cdef public: 
        int sequence2
        unsigned int total_num, num, data_size, current_pos
        object data

    cpdef read(self, ByteReader reader): # uses both
        self.sequence2 = reader.readShort(True) # seq at which this was sent at
        cdef int size = reader.readShort(True)
        self.total_num = reader.readInt(True) # total num
        self.num = reader.readInt(True) # packet num?
        self.data_size = reader.readInt(True) # total
        self.current_pos = reader.readInt(True) # current pos
        self.data = reader.readReader(size)
        
    cpdef write(self, ByteWriter reader):
        reader.writeShort(self.sequence2, True)
        reader.writeShort(len(self.data), True)
        reader.writeInt(self.total_num, True)
        reader.writeInt(self.num, True)
        reader.writeInt(self.data_size, True)
        reader.writeInt(self.current_pos, True)
        reader.write(str(self.data))

cdef class SizedSequenceData(PacketLoader):
    id = 9

    cdef public:
        int sequence2
        object data

    cpdef read(self, ByteReader reader): # uses byte
        self.sequence2 = reader.readShort(True) # sequence?
        cdef int size = reader.readShort(True)
        self.data = reader.readReader(size)
    
    cpdef write(self, ByteWriter reader):
        reader.writeShort(self.sequence2, True)
        reader.writeShort(len(self.data))
        reader.write(str(self.data))

cdef class Packet10(PacketLoader):
    id = 10

    cdef public:
        unsigned int dword_1, dword_2

    cpdef read(self, ByteReader reader):
        self.dword_1 = reader.readInt(True)
        self.dword_2 = reader.readInt(True)
        check_default_int(self.dword_1, 0)
        check_default_int(self.dword_2, 0)
    
    cpdef write(self, ByteWriter reader):
        reader.writeInt(self.dword_1, True)
        reader.writeInt(self.dword_2, True)

cdef class Packet11(PacketLoader):
    id = 11

    cdef public:
        unsigned int dword_1, dword_2, dword_3

    cpdef read(self, ByteReader reader):
        print 'THE MAGICAL PACKET11 (please send this to mat^2):',
        print repr(str(reader)),
        self.dword_1 = reader.readInt(True)
        self.dword_2 = reader.readInt(True)
        self.dword_3 = reader.readInt(True)
        print self.dword_1, self.dword_2, self.dword_3
    
    cpdef write(self, ByteWriter reader):
        reader.writeInt(self.dword_1, True)
        reader.writeInt(self.dword_2, True)
        reader.writeInt(self.dword_3, True)

__all__ = ['Ack', 'ConnectionRequest', 'ConnectionResponse', 'Disconnect',
    'Ping', 'SizedData', 'Packet7', 'MapData', 'SizedSequenceData', 'Packet10',
    'Packet11', 'Packet0']