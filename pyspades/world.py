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

from pyspades.common import *
import math
import time

def isvoxelsolid(map, x, y, z):
    if x < 0.0 or x > 512.0 or y < 0.0 or y > 512.0:
        return 1
    x = int(x)
    y = int(y)
    z = int(z)
    if z == 63:
        z = 62
    return map.get_solid(x, y, z)

def isvoxelsolid2(map, x, y, z):
    x = int(x) % 512
    y = int(y) % 512
    z = int(z)
    if z == 63:
        z = 62
    return map.get_solid(x, y, z)

class Object(object):
    name = 'object'
    def __init__(self, world, *arg, **kw):
        self.world = world
        self.initialize(*arg, **kw)
    
    def initialize(self, *arg, **kw):
        pass
    
    def update(self, dt):
        pass
    
    def delete(self):
        self.world.delete_object(self)

class Grenade(Object):
    name = 'grenade'
    def initialize(self, time_left, player_position, character, callback = None):
        self.callback = callback
        self.character = character
        self.position = Vertex3()
        self.acceleration = acceleration = Vertex3()
        self.position.set_vector(player_position)
        orientation = character.orientation
        player_acceleration = character.acceleration
        acceleration.x = orientation.x + player_acceleration.x
        acceleration.y = orientation.y + player_acceleration.y
        acceleration.z = orientation.z + player_acceleration.z
        self.time_left = time_left
    
    def collides(self, player_position):
        position = self.position
        player_x = int(player_position.x - 0.5)
        player_y = int(player_position.y - 0.5)
        player_z = int(player_position.z - 0.5)
        nade_x = int(position.x - 0.5)
        nade_y = int(position.y - 0.5)
        nade_z = int(position.z - 0.5)
        v19 = 0
        if nade_x >= player_x:
            if nade_x == player_x:
                v33 = 0.0
                v36 = 0.0
            else:
                v39 = 1
                v19 = nade_x - player_x
                v36 = player_x + 1 - player_position.x
                v33 = (position.x - player_position.x) * 1024.0
        else:
            v39 = -1
            v19 = player_x - nade_x
            v36 = player_position.x - player_x
            v33 = (player_position.x - position.x) * 1024.0
        if nade_y >= player_y:
            if nade_y == player_y:
                v34 = 0.0
                v37 = 0.0
            else:
                v19 += nade_y - player_y
                v40 = 1
                v37 = player_y + 1 - player_position.y
                v34 = (position.y - player_position.y) * 1024.0
        else:
            v19 += player_y - nade_y
            v40 = -1
            v37 = player_position.y - player_y
            v34 = (player_position.y - position.y) * 1024.0
        if nade_z >= player_z:
            if nade_z == player_z:
                v35 = 0.0
                v38 = 0.0
            else:
                v19 += nade_z - player_z
                v41 = 1
                v38 = player_z + 1 - player_position.z
                v35 = (position.z - player_position.z) * 1024.0
        else:
            v19 += player_z - nade_z
            v41 = -1
            v38 = player_position.z - player_z
            v35 = (player_position.z - position.z) * 1024.0
        v42 = v35 * v36 - v38 * v33
        v42_int = int(v42)
        v33_int = int(v33)
        v43 = v35 * v37 - v38 * v34
        v43_int = int(v43)
        v34_int = int(v34)
        v44 = v37 * v33 - v34 * v36
        v44_int = int(v44)
        v35_int = int(v35)
        if v19 <= 32:
            if not v19:
                return True
        else:
            v19 = 32
        v14 = v44_int
        v15 = v43_int
        v12 = v42_int
        map = self.world.map
        while 1:
            if (v12 | v15) < 0 or player_z == nade_z:
                if v14 < 0 or player_x == nade_x:
                    player_y += v40
                    v15 += v35_int
                    v14 += v33_int
                    v44_int = v14
                else:
                    player_x += v39
                    v12 += v35_int
                    v14 -= v34_int
                    v44_int = v14
            else:
                player_z += v41
                v12 -= v33_int
                v15 -= v34_int
            if isvoxelsolid2(map, player_x, player_y, player_z):
                break
            if v19 == 1:
                return True
            v19 -= 1
        return False
    
    def get_damage(self, player_position):
        position = self.position
        diff_x = player_position.x - position.x
        diff_y = player_position.y - position.y
        diff_z = player_position.z - position.z
        if (math.fabs(diff_x) < 16 and
            math.fabs(diff_y) < 16 and
            math.fabs(diff_z) < 16 and
            self.collides(player_position)):
            try:
                return 4096.0 / (diff_x**2 + diff_y**2 + diff_z**2)
            except ZeroDivisionError:
                return 100.0
    
    def update(self, dt):
        map = self.world.map
        position = self.position
        acceleration = self.acceleration
        self.time_left -= dt
        if self.time_left <= 0:
            # hurt players here
            if self.callback is not None:
                self.callback(self)
            self.delete()
            return
        acceleration.z += dt
        new_dt = dt * 32.0
        old_x = position.x
        old_y = position.y
        old_z = position.z
        position.x += acceleration.x * new_dt
        position.y += acceleration.y * new_dt
        position.z += acceleration.z * new_dt
        if not isvoxelsolid2(map, position.x, position.y, position.z):
            return
        collided = False
        if int(old_z) != int(position.z):
            if ((int(position.x) == int(old_x) and int(position.y) == int(old_y))
            or not isvoxelsolid2(map, position.x, position.y, old_z)):
                acceleration.z = -acceleration.z
                collided = True
        if not collided and int(old_x) != int(position.x):
            if ((int(old_y) == int(position.y) and int(old_z) == int(position.z))
            or not isvoxelsolid2(map, old_x, position.y, position.z)):
                acceleration.x = -acceleration.x
                collided = True
        if not collided and int(old_y) != int(position.y):
            if ((int(old_x) == int(position.x) and int(old_z) == int(position.z))
            or not isvoxelsolid2(map, position.x, old_y, position.z)):
                acceleration.y = -acceleration.y
                collided = True
        position.x = old_x
        position.y = old_y
        position.z = old_z
        acceleration.x *= 0.3600000143051147
        acceleration.y *= 0.3600000143051147
        acceleration.z *= 0.3600000143051147
        
class Character(Object):
    name = 'character'
    fire = jump = crouch = aim = False
    up = down = left = right = False
    
    null = False
    null2 = False
    last_time = 0.0
    guess_z = 0.0
    
    dead = False
    
    def initialize(self, position, orientation, fall_callback = None):
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
                    self.position.z += 0.8999999761581421
                else:
                    self.position.z -= 0.8999999761581421
            self.crouch = crouch
        if aim is not None:
            self.aim = aim
    
    def set_walk(self, up, down, left, right):
        self.up = up
        self.down = down
        self.left = left
        self.right = right
    
    def set_position(self, x, y, z, reset_acceleration = False):
        self.position.set(x, y, z)
        if reset_acceleration:
            self.acceleration.set(0.0, 0.0, 0.0)
        
    def set_orientation(self, x, y, z):
        self.orientation.set(x, y, z)
    
    def throw_grenade(self, time_left, callback = None):
        position = Vertex3(self.position.x, self.position.y, self.guess_z)
        item = self.world.create_object(Grenade, time_left, position, 
            self, callback)
        
    def update(self, dt):
        if self.dead:
            return
        orientation = self.orientation
        acceleration = self.acceleration
        if self.jump:
            self.jump = False
            acceleration.z = -0.3600000143051147
        v2 = self.null
        v3 = dt
        if v2:
            v4 = dt * 0.1000000014901161
            v3 = v4
        elif self.crouch:
            v3 = dt * 0.300000011920929
        elif self.aim:
            v3 = dt * 0.5
        if (self.up or self.down) and (self.left or self.right):
            v3 *= 0.7071067690849304
        if self.up:
            acceleration.x += orientation.x * v3
            acceleration.y += orientation.y * v3
        elif self.down:
            acceleration.x -= orientation.x * v3
            acceleration.y -= orientation.y * v3
        if self.left or self.right:
            xypow = math.sqrt(orientation.y**2 + orientation.x**2)
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
        v13 = dt + 1.0
        v9 = acceleration.z + dt
        acceleration.z = v9 / v13
        if not self.null2:
            if not self.null:
                v13 = dt * 4.0 + 1.0
        else:
            v13 = dt * 6.0 + 1.0
        acceleration.x /= v13
        acceleration.y /= v13
        old_acceleration = acceleration.z
        self.calculate_position(dt)
        if 0.0 != acceleration.z or old_acceleration <= 0.239999994635582:
            pass
        else:
            acceleration.x *= 0.5
            acceleration.y *= 0.5
            if old_acceleration > 0.4799999892711639:
                if self.fall_callback is not None:
                    self.fall_callback(-27 - old_acceleration**3 * -256.0)
    
    def calculate_position(self, dt):
        orientation = self.orientation
        acceleration = self.acceleration
        map = self.world.map
        position = self.position
        v1 = 0
        v4 = dt * 32.0
        v43 = acceleration.x * v4 + position.x
        v45 = acceleration.y * v4 + position.y
        v3 = 0.449999988079071
        if self.crouch:
            v47 = 0.449999988079071
            v5 = 0.8999999761581421
        else:
            v47 = 0.8999999761581421
            v5 = 1.350000023841858
        v31 = v5
        v29 = position.z + v47
        if acceleration.x < 0.0:
            v3 = -0.449999988079071
        v26 = v3
        v19 = v5
        if v31 >= -1.360000014305115:
            v38 = position.y - 0.449999988079071
            v32 = v43 + v26
            while 1:
                v6 = v19 + v29
                if isvoxelsolid(map, v32, v38, v6):
                    break
                v7 = v19 + v29
                v8 = position.y + 0.449999988079071
                if isvoxelsolid(map, v32, v8, v7):
                    break
                v19 -= 0.8999999761581421
                if v19 < -1.360000014305115:
                    break
        if v19 >= -1.360000014305115:
            if self.crouch or orientation.z >= 0.5:
                acceleration.x = 0
            else:
                v20 = 0.3499999940395355
                v39 = position.y - 0.449999988079071
                v33 = v43 + v26
                v9 = 0.3499999940395355
                while 1:
                    v23 = v9 + v29
                    if isvoxelsolid(map, v33, v39, v23):
                        v9 = v20
                        break
                    v10 = position.y + 0.449999988079071
                    if isvoxelsolid(map, v33, v10, v23):
                        v9 = v20
                        break
                    v20 -= 0.8999999761581421
                    v9 = v20
                    if v20 < -2.359999895095825:
                        break
                if v9 >= -2.359999895095825:
                    acceleration.x = 0.0
                else:
                    v1 = 1
                    position.x = v43
        else:
            position.x = v43
        if acceleration.y >= 0.0:
            v11 = 0.449999988079071
        else:
            v11 = -0.449999988079071
        v27 = v11
        v21 = v5
        if (v31 >= -1.360000014305115):
            v34 = position.x - 0.449999988079071
            v40 = v45 + v27
            while 1:
                v24 = v21 + v29
                if isvoxelsolid(map, v34, v40, v24):
                    break
                v12 = position.x + 0.449999988079071
                if isvoxelsolid(map, v12, v40, v24):
                    break
                v21 -= 0.8999999761581421
                if v21 < -1.360000014305115:
                    break
        label34 = False
        if v21 >= -1.360000014305115:
            if self.crouch or orientation.z >= 0.5:
                if v1:
                    label34 = True
            else:
                if v1:
                    label34 = True
                else:
                    v22 = 0.3499999940395355
                    v35 = position.x - 0.449999988079071
                    v41 = v45 + v27
                    v13 = 0.3499999940395355
                    while 1:
                        v25 = v13 + v29
                        if isvoxelsolid(map, v35, v41, v25):
                            v13 = v22
                            break
                        v14 = position.x + 0.449999988079071
                        if isvoxelsolid(map, v14, v41, v25):
                            v13 = v22
                            break
                        v22 -= 0.8999999761581421
                        v13 = v22
                        if v22 < -2.359999895095825:
                            break
                    if v13 < -2.359999895095825:
                        position.y = v45
                        label34 = True
            if not label34:
                acceleration.y = 0.0
        else:
            position.y = v45
            if v1:
                label34 = True
        if label34:
            acceleration.x *= 0.5
            acceleration.y *= 0.5
            self.last_time = time.time()
            v30 = v29 - 1.0
            v31 = -1.350000023841858
        else:
            if acceleration.z < 0.0:
                v31 = -v31
            v30 = acceleration.z * dt * 32.0 + v29
        self.null = 1
        v46 = v30 + v31
        v42 = position.y - 0.449999988079071
        v36 = position.x - 0.449999988079071
        flag = False
        if isvoxelsolid(map, v36, v42, v46):
            flag = True
        else:
            v44 = position.y + 0.449999988079071
            if isvoxelsolid(map, v36, v44, v46):
                flag = True
            else:
                v37 = position.x + 0.449999988079071
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
        v16 = self.last_time
        v28 = self.last_time - time.time()
        self.guess_z = position.z
        if v28 > -0.25:
            self.guess_z += (v28 + 0.25) * 4.0

class World(object):
    def __init__(self, map):
        self.objects = []
        self.map = map
    
    def update(self, dt):
        for instance in self.objects[:]:
            instance.update(dt)
            position = instance.position
    
    def delete_object(self, item):
        self.objects.remove(item)
        
    def create_object(self, klass, *arg, **kw):
        new_object = klass(self, *arg, **kw)
        self.objects.append(new_object)
        return new_object