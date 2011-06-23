from pyspades.bytes cimport ByteWriter, ByteReader

cdef class Loader:
    cpdef read(self, ByteReader reader)
    cpdef write(self, ByteWriter reader)
    cpdef ByteWriter generate(self)

cdef class PacketLoader(Loader):
    cdef public:
        bint ack
        int byte, sequence