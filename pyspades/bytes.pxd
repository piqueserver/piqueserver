from libc.math cimport NAN

DEF INT_ERROR = -0xFFFFFFFF >> 1
DEF LONG_LONG_ERROR = -0xFFFFFFFFFFFFFFFF >> 1

cdef extern from "<sstream>" namespace "std":
    cdef cppclass stringstream:
        pass

cdef class ByteReader:
    cdef char * data
    cdef char * pos
    cdef char * end
    cdef int start, size
    cdef object input

    cdef char * check_available(self, int size) except NULL
    cpdef read(self, int bytecount = ?)
    cpdef int readByte(self, bint unsigned = ?) except INT_ERROR
    cpdef int readShort(self, bint unsigned = ?, bint big_endian = ?) \
                        except INT_ERROR
    cpdef long long readInt(self, bint unsigned = ?, bint big_endian = ?) \
                            except LONG_LONG_ERROR
    cpdef float readFloat(self, bint big_endian = ?) except? NAN
    cpdef bytes readString(self, int size = ?)
    cpdef ByteReader readReader(self, int size = ?)
    cpdef int dataLeft(self)
    cdef void _skip(self, int bytecount)
    cpdef skipBytes(self, int bytecount)
    cpdef rewind(self, int value)
    cpdef seek(self, size_t pos)
    cpdef size_t tell(self)

cdef class ByteWriter:
    cdef stringstream * stream

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
    cpdef pad(self, int bytecount)
    cpdef rewind(self, int bytecount)
    cpdef size_t tell(self)
