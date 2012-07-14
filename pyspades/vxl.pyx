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

from pyspades.common cimport allocate_memory

cdef tuple make_color_tuple(int color):
    cdef int r, g, b, a
    b = color & 0xFF
    g = (color & 0xFF00) >> 8
    r = (color & 0xFF0000) >> 16
    a = (((color & 0xFF000000) >> 24) / 128.0) * 255
    return (r, g, b)

cpdef inline int make_color(int r, int g, int b, int a = 255):
    return b | (g << 8) | (r << 16) | (<int>((a / 255.0) * 128) << 24)

import time
import random

cdef class Generator:
    cdef MapGenerator * generator
    cdef public:
        bint done
    
    def __init__(self, VXLData data):
        self.done = False
        self.generator = create_map_generator(data.map)
    
    def get_data(self, int columns = 2):
        if self.done:
            return None
        value = get_generator_data(self.generator, columns)
        if not value:
            self.done = True
            return None
        return value
    
    def __dealloc__(self):
        delete_map_generator(self.generator)

cdef class VXLData:
    def __init__(self, fp = None):
        cdef unsigned char * c_data
        if fp is not None:
            data = fp.read()
            c_data = data
        else:
            c_data = NULL
        self.map = load_vxl(c_data)
    
    def load_vxl(self, c_data = None):
        self.map = load_vxl(c_data)
    
    def copy(self):
        cdef VXLData map = VXLData()
        map.map = copy_map(self.map)
        return map
    
    def get_point(self, int x, int y, int z):
        color = self.get_color(x, y, z)
        solid = color is not None
        return solid, color
    
    def set_point(self, int x, int y, int z, tuple color):
        if is_valid_position(x, y, z):
            set_point(x, y, z, self.map, 1, make_color(*color))

    cpdef get_solid(self, int x, int y, int z):
        if not is_valid_position(x, y, z):
            return None
        return get_solid(x, y, z, self.map)
    
    cpdef get_color(self, int x, int y, int z):
        if not self.get_solid(x, y, z):
            return None
        return make_color_tuple(get_color(x, y, z, self.map))
    
    cpdef int get_z(self, int x, int y, int start = 0):
        for z in xrange(start, 64):
            if get_solid(x, y, z, self.map):
                return z
        return 0
    
    cpdef int get_height(self, int x, int y):
        cdef int start = 63
        for z in xrange(start, -1, -1):
            if not get_solid(x, y, z, self.map):
                return z + 1
        return 0
    
    cpdef tuple get_random_point(self, int x1, int y1, int x2, int y2):
        cdef int x, y
        get_random_point(x1, y1, x2, y2, self.map, random.random(),
            random.random(), &x, &y)
        return x, y
    
    def count_land(self, int x1, y1, x2, y2):
        cdef int land = 0
        for x in xrange(x1, x2):
            for y in xrange(y1, y2):
                if self.get_solid(x, y, 62):
                    land += 1
        return land
    
    def destroy_point(self, int x, int y, int z):
        if not self.get_solid(x, y, z) or z >= 62:
            return False
        set_point(x, y, z, self.map, 0, 0)
        start = time.time()
        for node_x, node_y, node_z in self.get_neighbors(x, y, z):
            if node_z < 62:
                self.check_node(node_x, node_y, node_z, True)
        taken = time.time() - start
        if taken > 0.1:
            print 'destroying block at', x, y, z, 'took:', taken
        return True
    
    def remove_point(self, int x, int y, int z):
        if is_valid_position(x, y, z):
            set_point(x, y, z, self.map, 0, 0)
    
    cpdef bint has_neighbors(self, int x, int y, int z):
        return (
            self.get_solid(x + 1, y, z) or
            self.get_solid(x - 1, y, z) or
            self.get_solid(x, y + 1, z) or
            self.get_solid(x, y - 1, z) or
            self.get_solid(x, y, z + 1) or
            self.get_solid(x, y, z - 1)
        )
    
    cpdef bint is_surface(self, int x, int y, int z):
        return (
            not self.get_solid(x, y, z - 1) or
            not self.get_solid(x, y, z + 1) or
            not self.get_solid(x + 1, y, z) or
            not self.get_solid(x - 1, y, z) or
            not self.get_solid(x, y + 1, z) or
            not self.get_solid(x, y - 1, z)
        )
    
    cpdef list get_neighbors(self, int x, int y, int z):
        cdef list neighbors = []
        for (node_x, node_y, node_z) in (
            (x, y, z - 1),
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
    
    cpdef bint build_point(self, int x, int y, int z, tuple color):
        if not is_valid_position(x, y, z):
            return False
        if not self.has_neighbors(x, y, z) or z >= 62:
            return False
        r, g, b = color
        set_point(x, y, z, self.map, 1, make_color(*color))
        return True
    
    cpdef bint set_column_fast(self, int x, int y, int z_start,
        int z_end, int z_color_end, int color):
        """Set a column's solidity, but only color a limited amount from
            the top."""
        if (not is_valid_position(x, y, z_start) or
            not is_valid_position(x, y, z_end) or
            z_end < z_start):
            return False
        set_column_solid(x, y, z_start, z_end, self.map, 1)
        
        if not is_valid_position(x, y, z_color_end) or z_color_end < z_start:
            return False
        set_column_color(x, y, z_start, z_color_end, self.map, color)
        return True
    
    cpdef update_shadows(self):
        update_shadows(self.map)
    
    def get_overview(self, int z = -1, bint rgba = False):
        cdef unsigned int * data
        cdef unsigned int i, r, g, b, a, color
        data_python = allocate_memory(sizeof(int[512][512]), <char**>&data)
        i = 0
        cdef int current_z
        if z == -1:
            a = 255
        else:
            current_z = z
        for y in xrange(512):
            for x in xrange(512):
                if z == -1:
                    current_z = self.get_z(x, y)
                else:
                    if get_solid(x, y, z, self.map):
                        a = 255
                    else:
                        a = 0
                color = get_color(x, y, current_z, self.map)
                if rgba:
                    b = color & 0xFF
                    g = (color & 0xFF00) >> 8
                    r = (color & 0xFF0000) >> 16
                    data[i] = r | (g << 8) | (b << 16) | (a << 24)
                else:
                    data[i] = (color & 0x00FFFFFF) | (a << 24)
                i += 1
        return data_python
    
    def set_overview(self, data_str, int z):
        cdef unsigned int * data
        cdef unsigned int r, g, b, a, color, i, new_color
        data = <unsigned int*>(<char*>data_str)
        i = 0
        for y in xrange(512):
            for x in xrange(512):
                color = data[i]
                a = (color & <unsigned int>0xFF000000) >> 24
                if a != 255:
                    set_point(x, y, z, self.map, 0, 0)
                else:
                    set_point(x, y, z, self.map, 1, color)
                i += 1
    
    def generate(self):
        start = time.time()
        data = save_vxl(self.map)
        dt = time.time() - start
        if dt > 1.0:
            print 'VXLData.generate() took %s' % (dt)
        return data
    
    def get_generator(self):
        return Generator(self)
    
    def __dealloc__(self):
        cdef MapData * map
        if self.map != NULL:
            map = self.map
            self.map = NULL
            delete_vxl(map)