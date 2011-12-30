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

import math
import time
from pyspades.load cimport VXLData
from pyspades.common cimport Vertex3
from pyspades.constants import *

cdef extern from "math.h":
    double fabs(double x)

cdef extern from "world_c.cpp":
    int c_validate_hit "validate_hit" (
        float shooter_x, float shooter_y, float shooter_z,
        float orientation_x, float orientation_y, float orientation_z,
        float victim_x, float victim_y, float victim_z, float tolerance)
    int c_can_see "can_see" (void * map, float x0, float y0, float z0, float x1,
                             float y1, float z1)

from libc.math cimport sqrt

cdef inline bint isvoxelsolid(VXLData map, double x, double y, double z):
    if x < 0.0 or x > 512.0 or y < 0.0 or y > 512.0:
        return True
    cdef int x_int = <int>x
    cdef int y_int = <int>y
    cdef int z_int = <int>z
    if z_int == 63:
        z_int = 62
    elif z_int >= 64:
        return True
    return map.get_solid(x_int, y_int, z_int)

cdef inline bint isvoxelsolid2(VXLData map, double x, double y, double z):
    cdef int x_int = (<int>x) % 512
    cdef int y_int = (<int>y) % 512
    cdef int z_int = <int>z
    if z_int == 63:
        z_int = 62
    elif z_int >= 64:
        return True
    return map.get_solid(x_int, y_int, z_int)

cdef inline bint isvoxelsolidwrap(void * c_map, float x, float y, float z):
    cdef VXLData map = <VXLData>c_map
    return isvoxelsolid2(map, x, y, z);

cdef inline bint can_see(VXLData map, 
                         float x1, float y1, float z1,
                         float x2, float y2, float z2):
    return c_can_see(<void*>map, x1, y1, z1, x2, y2, z2)
                         

cdef class Object
cdef class World
cdef class Grenade
cdef class Character

cdef class Object:
    cdef public: 
        object name
        World world

    def __init__(self, world, *arg, **kw):
        self.world = world
        self.initialize(*arg, **kw)
        if self.name is None:
            self.name = 'object'
    
    def initialize(self, *arg, **kw):
        pass
    
    cdef int update(self, double dt) except -1:
        return 0
    
    def delete(self):
        self.world.delete_object(self)

cdef class Grenade(Object):
    cdef public:
        Vertex3 position
        Vertex3 acceleration
        double time_left
        object callback

    def initialize(self, double time_left, Vertex3 position, 
                   Vertex3 orientation, Vertex3 acceleration, callback = None):
        self.name = 'grenade'
        self.callback = callback
        self.position = Vertex3()
        self.acceleration = Vertex3()
        self.position.set_vector(position)
        if orientation is None:
            self.acceleration.set_vector(acceleration)
        else:
            self.acceleration.x = orientation.x + acceleration.x
            self.acceleration.y = orientation.y + acceleration.y
            self.acceleration.z = orientation.z + acceleration.z
        self.time_left = time_left
    
    cdef int hit_test(self, Vertex3 position):
        cdef Vertex3 nade = self.position
        return can_see(self.world.map, position.x, position.y, position.z,
                       nade.x, nade.y, nade.z)
    
    cpdef double get_damage(self, Vertex3 player_position):
        cdef Vertex3 position = self.position
        cdef double diff_x, diff_y, diff_z
        diff_x = player_position.x - position.x
        diff_y = player_position.y - position.y
        diff_z = player_position.z - position.z
        cdef double value
        if (fabs(diff_x) < 16 and
            fabs(diff_y) < 16 and
            fabs(diff_z) < 16 and
            self.hit_test(player_position)):
            value = diff_x**2 + diff_y**2 + diff_z**2
            if value == 0.0:
                return 100.0
            return 4096.0 / value
        return 0
    
    cdef int update(self, double dt) except -1:
        cdef VXLData map = self.world.map
        cdef Vertex3 position = self.position
        cdef Vertex3 acceleration = self.acceleration
        self.time_left -= dt
        if self.time_left <= 0:
            # hurt players here
            if self.callback is not None:
                self.callback(self)
            self.delete()
            return 0
        acceleration.z += dt
        cdef double new_dt = dt * 32.0
        cdef double old_x, old_y, old_z
        old_x = position.x
        old_y = position.y
        old_z = position.z
        position.x += acceleration.x * new_dt
        position.y += acceleration.y * new_dt
        position.z += acceleration.z * new_dt
        if not isvoxelsolid2(map, position.x, position.y, position.z):
            return 0
        cdef bint collided = False
        if <int>old_z != <int>position.z:
            if ((<int>position.x == <int>old_x and <int>position.y == <int>old_y)
            or not isvoxelsolid2(map, position.x, position.y, old_z)):
                acceleration.z = -acceleration.z
                collided = True
        if not collided and <int>old_x != <int>position.x:
            if ((<int>old_y == <int>position.y and <int>old_z == <int>position.z)
            or not isvoxelsolid2(map, old_x, position.y, position.z)):
                acceleration.x = -acceleration.x
                collided = True
        if not collided and <int>old_y != <int>position.y:
            if ((<int>old_x == <int>position.x and <int>old_z == <int>position.z)
            or not isvoxelsolid2(map, position.x, old_y, position.z)):
                acceleration.y = -acceleration.y
                collided = True
        position.x = old_x
        position.y = old_y
        position.z = old_z
        acceleration.x *= 0.36
        acceleration.y *= 0.36
        acceleration.z *= 0.36
        return 0
        
cdef class Character(Object):
    cdef public:
        Vertex3 position, orientation, acceleration
        bint fire, jump, crouch, aim
        bint up, down, left, right
        bint null, null2
        double last_time
        double guess_z
        bint dead
        object fall_callback
    
    def initialize(self, Vertex3 position, Vertex3 orientation, 
                   fall_callback = None):
        self.name = 'character'
        self.fire = self.jump = self.crouch = self.aim = False
        self.up = self.up = self.up = self.up = False
        self.null = self.null2
        self.last_time = 0.0
        self.guess_z = 0.0
        self.dead = False
        self.fall_callback = fall_callback
        self.position = Vertex3()
        self.orientation = Vertex3()
        self.acceleration = Vertex3()
        if position is not None:
            self.position.set_vector(position)
        if orientation is not None:
            self.orientation.set_vector(orientation)
    
    def set_animation(self, fire = None, jump = None, crouch = None, aim = None):
        if fire is not None:
            self.fire = fire
        if jump is not None:
            self.jump = jump
        if crouch is not None:
            if crouch != self.crouch:
                if crouch:
                    self.position.z += 0.9
                else:
                    self.position.z -= 0.9
            self.crouch = crouch
        if aim is not None:
            self.aim = aim
    
    def set_walk(self, bint up, bint down, bint left, bint right):
        self.up = up
        self.down = down
        self.left = left
        self.right = right
    
    def set_position(self, x, y, z, reset = False):
        self.position.set(x, y, z)
        if reset:
            self.acceleration.set(0.0, 0.0, 0.0)
            self.fire = self.jump = self.crouch = self.aim = False
            self.up = self.down = self.left = self.right = False
        
    def set_orientation(self, x, y, z):
        self.orientation.set(x, y, z)
    
    def throw_grenade(self, time_left, callback = None):
        position = Vertex3(self.position.x, self.position.y, self.guess_z)
        item = self.world.create_object(Grenade, time_left, position, 
            self.orientation, self.acceleration, callback)
        return item
    
    cpdef int can_see(self, float x, float y, float z):
        cdef Vertex3 position = self.position
        return can_see(self.world.map, position.x, position.y, position.z, 
            x, y, z)
    
    def validate_hit(self, Character other, part, float tolerance):
        cdef Vertex3 position1 = self.position
        cdef Vertex3 orientation = self.orientation
        cdef Vertex3 position2 = other.position
        cdef float x, y, z
        x = position2.x
        y = position2.y
        z = position2.z
        if part in (TORSO, ARMS):
            z += 0.9
        elif part == HEAD:
            pass
        elif part == LEGS:
            z += 1.8
        elif part == MELEE:
            z += 0.9
        else:
            return False
        if not c_validate_hit(position1.x, position1.y, position1.z,
                              orientation.x, orientation.y, orientation.z,
                              x, y, z, tolerance):
            return False
        # if part == HEAD:
            # z -= 0.5
        # if not can_see(self.world.map, x, y, z, 
                       # position1.x, position1.y, position1.z):
            # return False
        return True
        
    cdef int update(self, double dt) except -1:
        if self.dead:
            return 0
        cdef Vertex3 orientation = self.orientation
        cdef Vertex3 acceleration = self.acceleration
        if self.jump:
            self.jump = False
            acceleration.z = -0.36
        cdef int v2 = self.null
        cdef double v3 = dt
        cdef double v4
        if v2:
            v4 = dt * 0.1
            v3 = v4
        elif self.crouch:
            v3 = dt * 0.3
        elif self.aim:
            v3 = dt * 0.5
        if (self.up or self.down) and (self.left or self.right):
            v3 *= 0.70710678 # SQRT
        if self.up:
            acceleration.x += orientation.x * v3
            acceleration.y += orientation.y * v3
        elif self.down:
            acceleration.x -= orientation.x * v3
            acceleration.y -= orientation.y * v3
        
        cdef double xypow, orienty_over_xypow, orientx_over_xypow
        
        if self.left or self.right:
            xypow = sqrt(orientation.y**2 + orientation.x**2)
            if xypow == 0:
                orienty_over_xypow = orientx_over_xypow = 0
            else:
                orienty_over_xypow = -orientation.y / xypow
                orientx_over_xypow = orientation.x / xypow
            if self.left:
                acceleration.x -= orienty_over_xypow * v3
                acceleration.y -= orientx_over_xypow * v3
            else:
                acceleration.x += orienty_over_xypow * v3
                acceleration.y += orientx_over_xypow * v3
        cdef double v13 = dt + 1.0
        cdef double v9 = acceleration.z + dt
        acceleration.z = v9 / v13
        if not self.null2:
            if not self.null:
                v13 = dt * 4.0 + 1.0
        else:
            v13 = dt * 6.0 + 1.0
        acceleration.x /= v13
        acceleration.y /= v13
        cdef double old_acceleration = acceleration.z
        self.calculate_position(dt)
        if 0.0 != acceleration.z or old_acceleration <= 0.24:
            pass
        else:
            acceleration.x *= 0.5
            acceleration.y *= 0.5
            if self.fall_callback is not None and old_acceleration > 0.58:
                old_acceleration -= 0.58
                self.fall_callback(old_acceleration**2 * 4096)
        return 0
    
    cdef int calculate_position(self, double dt) except -1:
        cdef Vertex3 orientation = self.orientation
        cdef Vertex3 acceleration = self.acceleration
        cdef VXLData map = self.world.map
        cdef Vertex3 position = self.position
        cdef int v1 = 0
        cdef double v4 = dt * 32.0
        cdef double v43 = acceleration.x * v4 + position.x
        cdef double v45 = acceleration.y * v4 + position.y
        cdef double v3 = 0.45
        cdef double v47
        cdef double v5
        if self.crouch:
            v47 = 0.45
            v5 = 0.9
        else:
            v47 = 0.9
            v5 = 1.35
        cdef double v31 = v5
        cdef double v29 = position.z + v47
        if acceleration.x < 0.0:
            v3 = -0.45
        cdef double v26 = v3
        cdef double v19 = v5
        cdef double v38, v32, v6, v7, v8
        if v31 >= -1.36:
            v38 = position.y - 0.45
            v32 = v43 + v26
            while 1:
                v6 = v19 + v29
                if isvoxelsolid(map, v32, v38, v6):
                    break
                v7 = v19 + v29
                v8 = position.y + 0.45
                if isvoxelsolid(map, v32, v8, v7):
                    break
                v19 -= 0.9
                if v19 < -1.36:
                    break
        cdef double v20, v39, v33, v9, v23, v10, 
        if v19 >= -1.36:
            if self.crouch or orientation.z >= 0.5:
                acceleration.x = 0
            else:
                v20 = 0.35
                v39 = position.y - 0.45
                v33 = v43 + v26
                v9 = 0.35
                while 1:
                    v23 = v9 + v29
                    if isvoxelsolid(map, v33, v39, v23):
                        v9 = v20
                        break
                    v10 = position.y + 0.45
                    if isvoxelsolid(map, v33, v10, v23):
                        v9 = v20
                        break
                    v20 -= 0.9
                    v9 = v20
                    if v20 < -2.36:
                        break
                if v9 >= -2.36:
                    acceleration.x = 0.0
                else:
                    v1 = 1
                    position.x = v43
        else:
            position.x = v43
        cdef double v11
        if acceleration.y >= 0.0:
            v11 = 0.45
        else:
            v11 = -0.45
        cdef double v27 = v11
        cdef double v21 = v5
        cdef double v34, v40, v24, v12
        if v31 >= -1.36:
            v34 = position.x - 0.45
            v40 = v45 + v27
            while 1:
                v24 = v21 + v29
                if isvoxelsolid(map, v34, v40, v24):
                    break
                v12 = position.x + 0.45
                if isvoxelsolid(map, v12, v40, v24):
                    break
                v21 -= 0.9
                if v21 < -1.36:
                    break
        cdef bint label34 = False
        cdef double v22, v35, v41, v25, v14
        cdef double v13
        if v21 >= -1.36:
            if self.crouch or orientation.z >= 0.5:
                if v1:
                    label34 = True
            else:
                if v1:
                    label34 = True
                else:
                    v22 = 0.35
                    v35 = position.x - 0.45
                    v41 = v45 + v27
                    v13 = 0.35
                    while 1:
                        v25 = v13 + v29
                        if isvoxelsolid(map, v35, v41, v25):
                            v13 = v22
                            break
                        v14 = position.x + 0.45
                        if isvoxelsolid(map, v14, v41, v25):
                            v13 = v22
                            break
                        v22 -= 0.9
                        v13 = v22
                        if v22 < -2.36:
                            break
                    if v13 < -2.36:
                        position.y = v45
                        label34 = True
            if not label34:
                acceleration.y = 0.0
        else:
            position.y = v45
            if v1:
                label34 = True
        cdef double v30
        if label34:
            acceleration.x *= 0.5
            acceleration.y *= 0.5
            self.last_time = time.time()
            v30 = v29 - 1.0
            v31 = -1.35
        else:
            if acceleration.z < 0.0:
                v31 = -v31
            v30 = acceleration.z * dt * 32.0 + v29
        self.null = 1
        cdef double v46 = v30 + v31
        cdef double v42 = position.y - 0.45
        cdef double v36 = position.x - 0.45
        cdef bint flag = False
        cdef double v44, v37
        if isvoxelsolid(map, v36, v42, v46):
            flag = True
        else:
            v44 = position.y + 0.45
            if isvoxelsolid(map, v36, v44, v46):
                flag = True
            else:
                v37 = position.x + 0.45
                if isvoxelsolid(map, v37, v42, v46):
                    flag = True
                elif isvoxelsolid(map, v37, v44, v46):
                    flag = True
        if flag:
            if acceleration.z >= 0.0:
                self.null2 = position.z > 61.0
                self.null = 0
            acceleration.z = 0
        else:
            position.z = v30 - v47
        cdef double v16 = self.last_time
        cdef double v28 = self.last_time - time.time()
        self.guess_z = position.z
        if v28 > -0.25:
            self.guess_z += (v28 + 0.25) * 4.0
        return 0

cdef class World(object):
    cdef public:
        VXLData map
        list objects

    def __init__(self):
        self.objects = []
    
    def update(self, double dt):
        if self.map is None:
            return
        cdef Object instance
        for instance in self.objects[:]:
            instance.update(dt)
    
    cpdef delete_object(self, Object item):
        self.objects.remove(item)
        
    def create_object(self, klass, *arg, **kw):
        new_object = klass(self, *arg, **kw)
        self.objects.append(new_object)
        return new_object