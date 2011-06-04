cdef extern from *:
    ctypedef unsigned int uintptr_t

cdef extern from "stdlib.h":
    void free(void* ptr)
    void* malloc(size_t size)
    void* realloc(void* ptr, size_t size)
    void *memcpy(void *str1, void *str2, size_t n)
    
DEF XY_DIM = 512

cdef inline tuple get_color(color):
    cdef int a, b, c, d
    b = color & 0xFF
    g = (color & 0xFF00) >> 8
    r = (color & 0xFF0000) >> 16
    a = (((color & 0xFF000000) >> 24) / 128.0) * 255
    return (r, g, b, a)

cdef inline int make_color(int r, int g, int b, a):
    return b | (g << 8) | (r << 16) | (<int>((a / 255.0) * 128) << 24)

cdef inline unsigned int column_size(char * column):
    cdef char * v = column

    while 1:
        v+=v[0]*4
        if not v[0]:
            break
    return v - column + (v[2]-v[1]+1) * 4 + 4

from pyspades.bytes import ByteWriter

cdef class CompressedVXLData:
    cdef:
        char * columns[XY_DIM][XY_DIM]
        
    def __init__(self, data_python):
        cdef unsigned char * data = data_python
        
        cdef unsigned int chunks, top_color_start, top_color_end, air_start
        
        cdef int x, y
        
        for x in range(XY_DIM):
            for y in range(XY_DIM):
                start = data
                while 1:
                    chunks = data[0]
                    top_color_start = data[1]
                    top_color_end = data[2]
                    air_start = data[3]
                    if chunks == 0:
                        data += 4 * (top_color_end - top_color_start + 2)
                        break
                    data += chunks * 4
                new_data = <unsigned char *>malloc(data - start)
                memcpy(new_data, start, data - start)
                self.columns[x][y] = <char*>new_data
    
    cdef int get_floor(self, int x, int y, int z):

        if x|y >= XY_DIM: 
            return z
        cdef char * v = self.columns[x][y]
        while 1:
            if z <= v[1]:
                return v[1]
            if not v[0]:
                break
            v += v[0]*4;
            if z < v[3]:
                break
        return z
    
    cdef bint get_solid(self, int x, int y, int z):
        if x|y >= XY_DIM: 
            return 0
        cdef char * v = self.columns[x][y]
        while 1:
            if z < v[1]:
                return 0
            if not v[0]:
                return 1
            v += v[0]*4
            if z < v[3]:
                return 1
    
    cdef bint get_solid_range(self, int x, int y, int z0, int z1):
        if x|y >= XY_DIM: 
            return 0
        cdef char * v = self.columns[x][y]
        while 1:
            if z1 <= v[1]:
                return 0
            if not v[0]:
                return 1
            v += v[0] * 4
            if z0 < v[3]:
                return 1
    
    cdef bint get_empty_range(self, int x, int y, int z0, int z1):
        if x|y >= XY_DIM:
            return 1
        cdef char * v = self.columns[x][y]
        while 1:
            if z0 < v[1]:
                return 1
            if not v[0]:
                return 0
            v += v[0]*4;
            if z1 <= v[3]:
                return 0
    
    cdef uintptr_t _get_point(self, int x, int y, int z):
        if x|y >= XY_DIM:
            return 0
        cdef char * v = self.columns[x][y]
        cdef int ceilnum
        while 1:
            if z <= v[2]:
                if z < v[1]:
                    return 0
                return <uintptr_t>(&v[(z-v[1])*4+4])
                
            ceilnum = v[2]-v[1]-v[0]+2

            if not v[0]:
                return 1
            v += v[0]*4

            if z < v[3]:
                if z-v[3] < ceilnum:
                    return 1
                return <uintptr_t>(&v[(z-v[3])*4])
    
    # cdef void _set_point(self, int x, int y, int z, unsigned int color):
        # if x|y >= XY_DIM:
            # return
        # cdef char * v = self.columns[x][y]
        # cdef char * span_start
        # cdef char * span_end;
        # cdef int ceilnum
        # while 1:
            # if z <= v[2]:
                # if z < v[1]:
                    # return
                # return <uintptr_t>(&v[(z-v[1])*4+4])
                
            # ceilnum = v[2]-v[1]-v[0]+2

            # if not v[0]:
                # return 1
            # v += v[0]*4

            # if z < v[3]:
                # if z-v[3] < ceilnum:
                    # return
                # return <uintptr_t>(&v[(z-v[3])*4])
    
    def get_point(self, int x, int y, int z):
        cdef uintptr_t point = self._get_point(x, y, z)
        if point == 0:
            return 0, None
        elif point == 1:
            return 1, (0, 0, 0)
        else:
            return 1, get_color((<int*>point)[0])
    
    def set_point(self, int x, int y, int z, bint solid, tuple color_tuple):
        r, g, b, a = color_tuple
        cdef int color = b | (g << 8) | (r << 16) | (((a / 255.0) * 128) << 24)
        cdef char * data = self.columns[x][y]
    
    def generate(self):
        reader = ByteWriter()
        cdef int x, y
        cdef char * column
        for x in range(XY_DIM):
            for y in range(XY_DIM):
                column = self.columns[x][y]
                reader.write(column[:column_size(column)])
        return str(reader)