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
    struct MapData:
        pass
    MapData * load_vxl(unsigned char * v)
    void delete_vxl(MapData * map)
    object save_vxl(MapData * map)
    int check_node(int x, int y, int z, MapData * map, int destroy)
    bint get_solid(int x, int y, int z, MapData * map)
    int get_color(int x, int y, int z, MapData * map)
    void set_point(int x, int y, int z, MapData * map, bint solid, int color)

cdef inline tuple get_color_tuple(color):
    cdef int a, b, c, d
    b = color & 0xFF
    g = (color & 0xFF00) >> 8
    r = (color & 0xFF0000) >> 16
    a = (((color & 0xFF000000) >> 24) / 128.0) * 255
    return (r, g, b, a)

cdef inline int make_color(int r, int g, int b, a):
    return b | (g << 8) | (r << 16) | (<int>((a / 255.0) * 128) << 24)

import time
import random

cdef class VXLData:
    cdef MapData * map
    cdef list spawn_cache
        
    def __init__(self, fp = None):
        cdef unsigned char * c_data
        if fp is not None:
            data = fp.read()
            c_data = data
            self.map = load_vxl(c_data)
            self.cache_spawnable_land()
    
    def get_point(self, int x, int y, int z):
        return (get_solid(x, y, z, self.map), get_color_tuple(get_color(
            x, y, z, self.map)))
    
    cpdef int get_solid(self, int x, int y, int z):
        if (x not in range(512) or
            y not in range(512) or
            z not in range(64)):
            return 0
        return get_solid(x, y, z, self.map)
    
    def get_z(self, int x, int y, int start = 0):
        cdef int z
        for z in range(start, 64):
            if get_solid(x, y, z, self.map):
                return z
        return None
    
    cpdef int get_height(self, int x, int y):
        cdef int h_z
        for h_z in range(63, -1, -1):
            if not get_solid(x, y, h_z, self.map):
                return h_z + 1
        return 0
    
    def remove_point(self, int x, int y, int z, bint user = True):
        if x not in range(512) or y not in range(512) or z not in range(63):
            return
        if user and z == 62:
            return
        if not get_solid(x, y, z, self.map):
            return
        set_point(x, y, z, self.map, 0, 0)
        start = time.time()
        for node_x, node_y, node_z in self.get_neighbors(x, y, z):
            if node_z >= 62:
                continue
            self.check_node(node_x, node_y, node_z, True)
        taken = time.time() - start
        if taken > 0.1:
            print 'removing block at', x, y, z, 'took:', taken
    
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
            for (node_x, node_y, node_z) in ((x, y, z - 1),
                                             (x, y - 1, z),
                                             (x, y + 1, z),
                                             (x - 1, y, z),
                                             (x + 1, y, z),
                                             (x, y, z + 1)):
                if self.get_solid(node_x, node_y, node_z):
                    neighbors.append((node_x, node_y, node_z))
            return neighbors

    cpdef bint check_node(self, int x, int y, int z, bint destroy = False):
        return check_node(x, y, z, self.map, destroy)
    
    cpdef bint set_point(self, int x, int y, int z, tuple color_tuple, 
                         bint user = True):
        if user and (z not in range(62) or not self.has_neighbors(x, y, z)):
            return False
        r, g, b, a = color_tuple
        cdef int color = make_color(r, g, b, a)
        set_point(x, y, z, self.map, 1, color)
        return True
        
    def generate(self):
        return save_vxl(self.map)
    
    def __dealloc__(self):
        if self.map != NULL:
            delete_vxl(self.map)
    
    def cache_spawnable_land(self):
        self.spawn_cache = [[],[]]
        for team in [0,1]:
            for x in xrange(team*384,128):
                for y in xrange(128,256+128):
                    z = self.get_z(x, y)
                    if z>62:
                        continue
                    else:
                        self.spawn_cache[team].append((x,y,z))

    def get_random_spawnable(self, team):
        valid = self.spawn_cache[team]
        try:
            return random.choice(valid)
        except IndexError: # the spawn area is all water
            return None
