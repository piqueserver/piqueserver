from pyspades.common import *
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
    def initialize(self, time_left, player_position, character):
        self.character = character
        self.position = Vertex3()
        self.acceleration = acceleration = Vertex3()
        self.position.set_vector(player_position)
        orientation = character.orientation
        player_acceleration = character.acceleration
        acceleration.x = orientation.x + player_acceleration.x
        acceleration.y = orientation.y + player_acceleration.y
        acceleration.z = orientation.z + player_acceleration.z
        self.explode_time = time.time() + time_left
    
    def destroy(self):
        self.character.grenades.remove(self)
        self.delete()
    
    def update(self, dt):
        map = self.world.map
        position = self.position
        acceleration = self.acceleration
        if self.explode_time < time.time():
            # hurt players here
            self.character.grenades.remove(self)
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
    fire = jump = crouch = aim = False
    up = down = left = right = False
    
    null = False
    null2 = False
    last_time = 0.0
    guess_z = 0.0
    
    def initialize(self, position, orientation):
        self.position = Vertex3()
        self.orientation = Vertex3()
        self.acceleration = Vertex3()
        self.position.set_vector(position)
        self.orientation.set_vector(orientation)
        self.grenades = []
    
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
    
    def throw_grenade(self, time_left):
        position = Vertex3(self.position.x, self.position.y, self.guess_z)
        item = self.world.create_object(Grenade, time_left, position, 
            self)
        self.grenades.append(item)
        
    def update(self, dt):
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
                self.on_fall(-27 - old_acceleration**3 * -256.0)
    
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
    
    def on_fall(self, damage):
        print 'on fall, damage:', damage

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