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

cdef extern from "Python.h":
    object PyString_FromStringAndSize(char*,Py_ssize_t)
    char* PyString_AS_STRING(object)
    int Py_REFCNT(object v)

cdef extern from "stdlib.h":
    void free(void* ptr)
    void* malloc(size_t size)
    void* realloc(void* ptr, size_t size)
    void *memcpy(void *str1, void *str2, size_t n)

cdef inline object allocate_memory(int size, char ** i):
    if size < 0: 
        size = 0
    cdef object ob = PyString_FromStringAndSize(NULL, size)
    i[0] = PyString_AS_STRING(ob)
    return ob

cdef extern from "load_c.cpp":
    enum:
        MAP_X
        MAP_Y
        MAP_Z
    void load_vxl(unsigned char * v, long colors[][MAP_Y][MAP_Z], 
        char geometry[][MAP_Y][MAP_Z])
    object save_vxl(long color[][MAP_Y][MAP_Z], char map[][MAP_Y][MAP_Z])

cdef inline tuple get_color(color):
    cdef int a, b, c, d
    b = color & 0xFF
    g = (color & 0xFF00) >> 8
    r = (color & 0xFF0000) >> 16
    a = (((color & 0xFF000000) >> 24) / 128.0) * 255
    return (r, g, b, a)

cdef class VXLData:
    cdef:
        long colors[MAP_X][MAP_Y][MAP_Z]
        char geometry[MAP_X][MAP_Y][MAP_Z]
        object colors_python, geometry_python
        
    def __init__(self, fp):
        data = fp.read()
        cdef unsigned char * c_data = data
        load_vxl(c_data, self.colors, self.geometry)
    
    def get_point(self, int x, int y, int z):
        cdef long color = self.colors[x][y][z]
        cdef char solid = self.geometry[x][y][z]
        cdef int a, b, c, d
        b = color & 0xFF
        g = (color & 0xFF00) >> 8
        r = (color & 0xFF0000) >> 16
        a = (((color & 0xFF000000) >> 24) / 128.0) * 255
        return (solid, (r, g, b, a))
    
    def set_point(self, int x, int y, int z, char solid, tuple color_tuple):
        r, g, b, a = color_tuple
        cdef int color = b | (g << 8) | (r << 16) | (((a / 255.0) * 128) << 24)
        self.geometry[x][y][z] = solid
        self.color[x][y][z] = color
        
    def generate(self):
        return save_vxl(self.colors, self.geometry)