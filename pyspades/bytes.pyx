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

"""
Reads/writes bytes
"""

cdef extern from "bytes_c.cpp":
    char read_byte(char * data)
    unsigned char read_ubyte(char * data)
    short read_short(char * data, int big_endian)
    unsigned short read_ushort(char * data, int big_endian)
    int read_int(char * data, int big_endian)
    unsigned int read_uint(char * data, int big_endian)
    double read_float(char * data, int big_endian)
    char * read_string(char * data)

    void * create_stream()
    void delete_stream(void * stream)
    void write_byte(void * stream, char value)
    void write_ubyte(void * stream, unsigned char value)
    void write_short(void * stream, short value, int big_endian)
    void write_ushort(void * stream, unsigned short value, int big_endian)
    void write_int(void * stream, int value, int big_endian)
    void write_uint(void * stream, unsigned int value, int big_endian)
    void write_float(void * stream, double value, int big_endian)
    void write_string(void * stream, char * data, size_t size)
    void write(void * stream, char * data, size_t size)
    void rewind_stream(void * stream, int bytes)
    object get_stream(void * stream)
    size_t get_stream_size(void * stream)
    size_t get_stream_pos(void * stream)

class NoDataLeft(Exception):
    pass

DEF INT_ERROR = -0xFFFFFFFF >> 1
DEF LONG_LONG_ERROR = -0xFFFFFFFFFFFFFFFF >> 1
DEF FLOAT_ERROR = float('nan')

cdef class ByteReader:
    def __init__(self, input, int start = 0, int size = -1):
        self.input = input
        self.data = input
        self.data += start
        self.pos = self.data
        if size == -1:
            size = len(input) - start
        self.size = size
        self.end = self.data + size
        self.start = start

    cdef char * check_available(self, int size) except NULL:
        cdef char * data = self.pos
        if data + size > self.end:
            raise NoDataLeft('not enough data')
        self.pos += size
        return data

    cpdef read(self, int bytes = -1):
        cdef int left = self.dataLeft()
        if bytes == -1 or bytes > left:
            bytes = left
        ret = self.pos[:bytes]
        self.pos += bytes
        return ret

    cpdef int readByte(self, bint unsigned = False) except INT_ERROR:
        cdef char * pos = self.check_available(1)
        if unsigned:
            return read_ubyte(pos)
        else:
            return read_byte(pos)

    cpdef int readShort(self, bint unsigned = False, bint big_endian = True) \
                        except INT_ERROR:
        cdef char * pos = self.check_available(2)
        if unsigned:
            return read_ushort(pos, big_endian)
        else:
            return read_short(pos, big_endian)

    cpdef long long readInt(self, bint unsigned = False,
                            bint big_endian = True) except LONG_LONG_ERROR:
        cdef char * pos = self.check_available(4)
        if unsigned:
            return read_uint(pos, big_endian)
        else:
            return read_int(pos, big_endian)

    cpdef float readFloat(self, bint big_endian = True) except? FLOAT_ERROR:
        cdef char * pos = self.check_available(4)
        return read_float(pos, big_endian)

    cpdef readString(self, int size = -1):
        value = self.pos
        if size == -1:
            size = len(value) + 1
        if size > self.end - self.pos:
            size = self.end - self.pos
            value = value[:size]
        self.pos += size
        return value

    cpdef ByteReader readReader(self, int size = -1):
        cdef int left = self.dataLeft()
        if size == -1 or size > left:
            size = left
        cdef ByteReader reader = ByteReader(self.input,
            (self.pos - self.data) + self.start, size)
        self.pos += size
        return reader

    cpdef size_t tell(self):
        return self.pos - self.data

    cpdef int dataLeft(self):
        return self.end - self.pos

    cpdef seek(self, size_t pos):
        self.pos = self.data + pos
        if self.pos > self.end:
            self.pos = self.end
        if self.pos < self.data:
            self.pos = self.data

    cdef void _skip(self, int bytes):
        self.pos += bytes
        if self.pos > self.end:
            self.pos = self.end
        if self.pos < self.data:
            self.pos = self.data

    cpdef skipBytes(self, int bytes):
        self._skip(bytes)

    cpdef rewind(self, int value):
        self._skip(-value)

    def __len__(self):
        return self.size

    def __str__(self):
        return self.data[:self.size]

cdef class ByteWriter:
    def __init__(self):
        self.stream = create_stream()

    cdef void writeSize(self, char * data, int size):
        write(self.stream, data, size)

    cpdef write(self, data):
        write(self.stream, data, len(data))

    cpdef writeByte(self, int value, bint unsigned = False):
        if unsigned:
            write_ubyte(self.stream, value)
        else:
            write_byte(self.stream, value)

    cpdef writeShort(self, int value, bint unsigned = False,
                     bint big_endian = True):
        if unsigned:
            write_ushort(self.stream, value, big_endian)
        else:
            write_short(self.stream, value, big_endian)

    cpdef writeInt(self, long long value, bint unsigned = False,
                   bint big_endian = True):
        if unsigned:
            write_uint(self.stream, value, big_endian)
        else:
            write_int(self.stream, value, big_endian)

    cpdef writeFloat(self, float value, bint big_endian = True):
        write_float(self.stream, value, big_endian)

    cpdef writeStringSize(self, char * value, int size):
        write_string(self.stream, value, size)

    cpdef writeString(self, value, int size = -1):
        write_string(self.stream, value, len(value))
        if size != -1:
            self.pad(size - (len(value) + 1))

    cpdef pad(self, int bytes):
        cdef int i
        for i in range(bytes):
            write_ubyte(self.stream, 0)

    cpdef rewind(self, int bytes):
        rewind_stream(self.stream, bytes)

    cpdef size_t tell(self):
        return get_stream_pos(self.stream)

    def __str__(self):
        return get_stream(self.stream)

    def __dealloc__(self):
        delete_stream(self.stream)

    def __len__(self):
        return get_stream_size(self.stream)
