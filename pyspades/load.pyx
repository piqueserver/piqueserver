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

cdef inline object allocate_memory(int size, char ** i):
    if size < 0: 
        size = 0
    cdef object ob = PyString_FromStringAndSize(NULL, size)
    i[0] = PyString_AS_STRING(ob)
    return ob

cdef extern from "load_c.c":
    void load_vxl(unsigned char * v, long * colors, int * geometry)
    int get_pos(int x, int y, int z)

cdef class VXLData:
    cdef:
        long * colors
        int * geometry
        object colors_python, geometry_python
        
    def __init__(self, fp):
        cdef int * geometry
        cdef long * colors
        self.colors_python = allocate_memory(
            512 * 512 * 64 * sizeof(long), <char **>(&colors))
        self.geometry_python = allocate_memory(
            512 * 512 * 64 * sizeof(int), <char **>(&geometry))
        self.geometry = geometry
        self.colors = colors
        data = fp.read()
        cdef unsigned char * c_data = data
        load_vxl(c_data, colors, geometry)
    
    def get_point(self, x, y, z):
        cdef int pos = x + y * 512 + z * 512 * 512
        cdef long color = self.colors[pos]
        cdef bint solid = self.geometry[pos]
        cdef int a, b, c, d
        b = color & 0xFF
        g = (color & 0xFF00) >> 8
        r = (color & 0xFF0000) >> 16
        a = (((color & 0xFF000000) >> 24) / 128.0) * 255
        return (solid, (r, g, b, a))