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

import math
import time
from pyspades.vxl cimport VXLData, MapData
from pyspades.common cimport Vertex3, create_proxy_vector
from pyspades.constants import *

cdef extern from "math.h":
    double fabs(double x)

cdef extern from "common_c.h":
    struct LongVector:
        int x, y, z
    struct Vector:
        float x, y, z

cdef extern from "world_c.cpp":
    enum:
        CUBE_ARRAY_LENGTH
    int c_validate_hit "validate_hit" (
        float shooter_x, float shooter_y, float shooter_z,
        float orientation_x, float orientation_y, float orientation_z,
        float victim_x, float victim_y, float victim_z, float tolerance)
    int c_can_see "can_see" (MapData * map, float x0, float y0, float z0,
        float x1, float y1, float z1)
    int c_cast_ray "cast_ray" (MapData * map, float x0, float y0, float z0,
        float x1, float y1, float z1, float length, long* x, long* y, long* z)
    size_t cube_line_c "cube_line"(int, int, int, int, int, int, LongVector *)
    void set_globals(MapData * map, float total_time, float dt)
    struct PlayerType:
        Vector p, e, v, s, h, f
        int mf, mb, ml, mr
        int jump, crouch, sneak
        int airborne, wade, alive, sprint
        int primary_fire, secondary_fire, weapon

    struct GrenadeType:
        Vector p, v
    PlayerType * create_player()
    void destroy_player(PlayerType * player)
    void destroy_grenade(GrenadeType * player)
    void update_timer(float value, float dt)
    void reorient_player(PlayerType * p, Vector * vector)
    int move_player(PlayerType * p)
    void set_globals(MapData * map)
    int try_uncrouch(PlayerType * p)
    GrenadeType * create_grenade(Vector * p, Vector * v)
    int move_grenade(GrenadeType * grenade)

from libc.math cimport sqrt

cdef inline bint can_see(VXLData map, float x1, float y1, float z1,
    float x2, float y2, float z2):
    return c_can_see(map.map, x1, y1, z1, x2, y2, z2)

cdef inline bint cast_ray(VXLData map, float x1, float y1, float z1,
    float x2, float y2, float z2, float length, long* x, long* y, long* z):
    return c_cast_ray(map.map, x1, y1, z1, x2, y2, z2, length, x, y, z)

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

cdef class Character(Object):
    cdef:
        PlayerType * player
    cdef public:
        Vertex3 position, orientation, velocity
        object fall_callback

    def initialize(self, Vertex3 position, Vertex3 orientation,
                   fall_callback = None):
        self.name = 'character'
        self.player = create_player()
        self.fall_callback = fall_callback
        self.position = create_proxy_vector(&self.player.p)
        self.orientation = create_proxy_vector(&self.player.f)
        self.velocity = create_proxy_vector(&self.player.v)
        if position is not None:
            self.set_position(*position.get())
        if orientation is not None:
            self.orientation.set_vector(orientation)

    def set_crouch(self, bint value):
        if value == self.player.crouch:
            return
        if value:
            self.player.p.z += 0.9
        else:
            self.player.p.z -= 0.9
        self.player.crouch = value

    def set_animation(self, jump, crouch, sneak, sprint):
        self.player.jump = jump
        self.set_crouch(crouch)
        self.player.sneak = sneak
        self.player.sprint = sprint

    def set_weapon(self, is_primary):
        self.player.weapon = is_primary

    def set_walk(self, up, down, left, right):
        self.player.mf = up
        self.player.mb = down
        self.player.ml = left
        self.player.mr = right

    def set_position(self, x, y, z, reset = False):
        self.position.set(x, y, z)
        self.player.p.x = self.player.e.x = x
        self.player.p.y = self.player.e.y = y
        self.player.p.z = self.player.e.z = z
        if reset:
            self.velocity.set(0.0, 0.0, 0.0)
            self.primary_fire = self.secondary_fire = False
            self.jump = self.crouch = False
            self.up = self.down = self.left = self.right = False

    def set_orientation(self, x, y, z):
        cdef Vertex3 v = Vertex3(x, y, z)
        reorient_player(self.player, v.value)

    cpdef int can_see(self, float x, float y, float z):
        cdef Vertex3 position = self.position
        return can_see(self.world.map, position.x, position.y, position.z,
            x, y, z)

    cpdef cast_ray(self, length = 32.0):
        cdef Vertex3 position = self.position
        cdef Vertex3 direction = self.orientation.copy().normal()
        cdef long x, y, z
        if cast_ray(self.world.map, position.x, position.y, position.z,
            direction.x, direction.y, direction.z, length, &x, &y, &z):
            return x, y, z
        return None

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
        return True

    def set_dead(self, value):
        self.player.alive = not value
        self.player.mf = False
        self.player.mb = False
        self.player.ml = False
        self.player.mr = False
        self.player.crouch = False
        self.player.sneak = False
        self.player.primary_fire = False
        self.player.secondary_fire = False
        self.player.sprint = False

    cdef int update(self, double dt) except -1:
        cdef long ret = move_player(self.player)
        if ret > 0:
            self.fall_callback(ret)
        return 0

    # properties
    property up:
        def __get__(self):
            return self.player.mf
        def __set__(self, value):
            self.player.mf = value

    property down:
        def __get__(self):
            return self.player.mb
        def __set__(self, value):
            self.player.mb = value

    property left:
        def __get__(self):
            return self.player.ml
        def __set__(self, value):
            self.player.ml = value

    property right:
        def __get__(self):
            return self.player.mr
        def __set__(self, value):
            self.player.mr = value

    property dead:
        def __get__(self):
            return not self.player.alive
        def __set__(self, bint value):
            self.set_dead(value)

    property jump:
        def __get__(self):
            return self.player.jump
        def __set__(self, value):
            self.player.jump = value

    property airborne:
        def __get__(self):
            return self.player.airborne

    property crouch:
        def __get__(self):
            return self.player.crouch
        def __set__(self, value):
            self.player.crouch = value

    property sneak:
        def __get__(self):
            return self.player.sneak
        def __set__(self, value):
            self.player.sneak = value

    property wade:
        def __get__(self):
            return self.player.wade

    property sprint:
        def __get__(self):
            return self.player.sprint
        def __set__(self, value):
            self.player.sprint = value

    property primary_fire:
        def __get__(self):
            return self.player.primary_fire
        def __set__(self, value):
            self.player.primary_fire = value

    property secondary_fire:
        def __get__(self):
            return self.player.secondary_fire
        def __set__(self, value):
            self.player.secondary_fire = value

cdef class Grenade(Object):
    cdef public:
        Vertex3 position, velocity
        float fuse
        object callback
        object team
    cdef GrenadeType * grenade

    def initialize(self, double fuse, Vertex3 position, Vertex3 orientation,
                   Vertex3 velocity, callback = None):
        self.name = 'grenade'
        self.grenade = create_grenade(position.value, velocity.value)
        self.position = create_proxy_vector(&self.grenade.p)
        self.velocity = create_proxy_vector(&self.grenade.v)
        if orientation is not None:
            self.velocity += orientation
        self.fuse = fuse
        self.callback = callback

    cdef int hit_test(self, Vertex3 position):
        cdef Vector * nade = self.position.value
        return can_see(self.world.map, position.x, position.y, position.z,
                       nade.x, nade.y, nade.z)

    cpdef get_next_collision(self, double dt):
        if self.velocity.is_zero():
            return None
        cdef double eta = 0.0
        cdef double x, y, z
        cdef Vertex3 old_position = self.position.copy()
        cdef Vertex3 old_velocity = self.velocity.copy()
        while move_grenade(self.grenade) == 0:
            eta += dt
            if eta > 5.0:
                break
        x, y, z = self.position.x, self.position.y, self.position.z
        self.position.set_vector(old_position)
        self.velocity.set_vector(old_velocity)
        return eta, x, y, z

    cpdef double get_damage(self, Vertex3 player_position):
        cdef Vector * position = self.position.value
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
        self.fuse -= dt
        if self.fuse <= 0:
            if self.callback is not None:
                self.callback(self)
            self.delete()
            return 0
        move_grenade(self.grenade)

    def __dealloc__(self):
        destroy_grenade(self.grenade)

cdef class World(object):
    cdef public:
        VXLData map
        list objects
        float time

    def __init__(self):
        self.objects = []
        self.time = 0

    def update(self, double dt):
        if self.map is None:
            return
        self.time += dt
        set_globals(self.map.map, self.time, dt)
        cdef Object instance
        for instance in self.objects[:]:
            instance.update(dt)

    cpdef delete_object(self, Object item):
        self.objects.remove(item)

    def create_object(self, klass, *arg, **kw):
        new_object = klass(self, *arg, **kw)
        self.objects.append(new_object)
        return new_object

# utility functions

cpdef cube_line(x1, y1, z1, x2, y2, z2):
    cdef LongVector array[CUBE_ARRAY_LENGTH]
    cdef size_t size = cube_line_c(x1, y1, z1, x2, y2, z2, array)
    cdef size_t i
    cdef list points = []
    for i in xrange(size):
        points.append((array[i].x, array[i].y, array[i].z))
    return points
