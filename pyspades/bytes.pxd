cdef class ByteReader:
    cdef char * data
    cdef char * pos
    cdef char * end
    cdef int start, size
    cdef object input
    
    cdef char * check_available(self, int size) except NULL
    cpdef read(self, int bytes = ?)
    cpdef int readByte(self, bint unsigned = ?)
    cpdef int readShort(self, bint unsigned = ?, bint big_endian = ?)
    cpdef long long readInt(self, bint unsigned = ?, bint big_endian = ?)
    cpdef float readFloat(self, bint big_endian = ?)
    cpdef readString(self, int size = ?)
    cpdef ByteReader readReader(self, int size = ?)
    cpdef int dataLeft(self)
    cdef void _skip(self, int bytes)
    cpdef skipBytes(self, int bytes)
    cpdef rewind(self, int value)

cdef class ByteWriter:
    cdef void * stream
    
    cdef void writeSize(self, char * data, int size)
    cpdef write(self, data)
    cpdef writeByte(self, int value, bint unsigned = ?)
    cpdef writeShort(self, int value, bint unsigned = ?, 
                     bint big_endian = ?)
    cpdef writeInt(self, long long value, bint unsigned = ?, 
                   bint big_endian = ?)
    cpdef writeFloat(self, float value, bint big_endian = ?)
    cpdef writeStringSize(self, char * value, int size)
    cpdef writeString(self, value, int size = ?)
    cpdef pad(self, int bytes)
    cpdef rewind(self, int bytes)