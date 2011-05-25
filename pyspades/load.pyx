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
        DEFAULT_COLOR
    void load_vxl(unsigned char * v, int (*colors)[MAP_X][MAP_Y][MAP_Z], 
                                     char (*geometry)[MAP_X][MAP_Y][MAP_Z],
                                     char (*heightmap)[MAP_X][MAP_Y])
    object save_vxl(int (*color)[MAP_X][MAP_Y][MAP_Z], char (*map)[MAP_X][MAP_Y][MAP_Z])
    void destroy_floating_blocks(int x, int y, int z, 
                                 char (*map)[MAP_X][MAP_Y][MAP_Z])

from pyspades.block import check_node

cdef inline tuple get_color(color):
    cdef int a, b, c, d
    b = color & 0xFF
    g = (color & 0xFF00) >> 8
    r = (color & 0xFF0000) >> 16
    a = (((color & 0xFF000000) >> 24) / 128.0) * 255
    return (r, g, b, a)

cdef inline int make_color(int r, int g, int b, a):
    return b | (g << 8) | (r << 16) | (<int>((a / 255.0) * 128) << 24)

cdef class VXLData:
    cdef:
        int (*colors)[MAP_X][MAP_Y][MAP_Z]
        char (*geometry)[MAP_X][MAP_Y][MAP_Z]
        char (*heightmap)[MAP_X][MAP_Y]
        object colors_python, geometry_python, heightmap_python
        
    def __init__(self, fp = None):
        self.colors_python = allocate_memory(sizeof(int[MAP_X][MAP_Y][MAP_Z]),
            <char**>&self.colors)
        self.geometry_python = allocate_memory(sizeof(char[MAP_X][MAP_Y][MAP_Z]),
            <char**>&self.geometry)
        self.heightmap_python = allocate_memory(sizeof(char[MAP_X][MAP_Y]),
            <char**>&self.heightmap)
        cdef unsigned char * c_data
        if fp is not None:
            data = fp.read()
            c_data = data
            load_vxl(c_data, self.colors, self.geometry, self.heightmap)
    
    def get_point(self, int x, int y, int z):
        cdef int color = self.colors[0][x][y][z]
        if color == 0:
            color = DEFAULT_COLOR
        cdef char solid = self.geometry[0][x][y][z]
        return (solid, get_color(color))
    
    cpdef int get_solid(self, int x, int y, int z):
        if (x not in range(512) or
            y not in range(512) or
            z not in range(64)):
            return 0
        return self.geometry[0][x][y][z]
    
    def get_z(self, int x, int y, int start = 0):
        cdef int z
        for z in range(start, 64):
            if self.geometry[0][x][y][z]:
                return z
        return None
    
    def get_height(self, int x, int y):
        return self.heightmap[0][x][y]
    
    def remove_point(self, int x, int y, int z):
        if x not in range(512) or y not in range(512) or z not in range(63):
            return
        if not self.geometry[0][x][y][z]:
            return
        self.geometry[0][x][y][z] = 0
        self.update_heightmap(x, y)
        for node_x, node_y, node_z in self.get_neighbors(x, y, z):
            if node_z >= 62:
                continue
            if not check_node(self, node_x, node_y, node_z):
                destroy_floating_blocks(node_x, node_y, node_z, self.geometry)
    
    cpdef bint has_neighbors(self, int x, int y, int z):
        return (
            self.get_solid(x + 1, y, z) or
            self.get_solid(x - 1, y, z) or
            self.get_solid(x, y + 1, z) or
            self.get_solid(x, y - 1, z) or
            self.get_solid(x, y, z + 1) or
            self.get_solid(x, y, z - 1)
        )
    
    cpdef list get_neighbors(self, int x, int y, int z):
        cdef list neighbors = []
        for (node_x, node_y, node_z) in  ((x + 1, y, z),
                                         (x - 1, y, z),
                                         (x, y + 1, z),
                                         (x, y - 1, z),
                                         (x, y, z + 1),
                                         (x, y, z - 1)):
            if self.get_solid(node_x, node_y, node_z):
                neighbors.append((node_x, node_y, node_z))
        return neighbors
    
    cdef inline void update_heightmap(self, int x, int y):
        cdef int h_z
        for h_z in range(63, -1, -1):
            if not self.geometry[0][x][y][h_z]:
                self.heightmap[0][x][y] = h_z + 1
                break
        else:
            self.heightmap[0][x][y] = 0
    
    cpdef bint set_point(self, int x, int y, int z, tuple color_tuple):
        if not self.has_neighbors(x, y, z):
            return False
        r, g, b, a = color_tuple
        cdef int color = make_color(r, g, b, a)
        self.geometry[0][x][y][z] = 1
        self.colors[0][x][y][z] = color
        self.update_heightmap(x, y)
        return True
        
    def generate(self):
        return save_vxl(self.colors, self.geometry)