from commands import add, admin
from pyspades.contained import BlockAction, SetColor
from pyspades.constants import *
from math import *

EAST = 0
SOUTH = 1
WEST = 2
NORTH = 3

def make_color(r, g, b, a):
    return b | (g << 8) | (r << 16) | (int((a / 255.0) * 128) << 24)

def make_color_tuple(color):
    return make_color(color[0], color[1], color[2], 255)

def get_color_tuple(color):
    b = color & 0xFF
    g = (color & 0xFF00) >> 8
    r = (color & 0xFF0000) >> 16
    a = int((((color & 0xFF000000) >> 24) / 128.0) * 255)
    return (r, g, b, a)

def set_color(prt, color, player_id = 32):
    c = SetColor()
    c.player_id = player_id
    c.value = color
    prt.send_contained(c)

def add_block(prt, x, y, z, color, player_id = 32, mirror_x = False, mirror_y = False):
    if x >= 0 and x < 512 and y >= 0 and y < 512 and z >= 0 and z < 64:
        if mirror_x == True or mirror_y == True:
            x2 = x
            y2 = y
            if mirror_x == True:
                x2 = 511 - x
            if mirror_y == True:
                y2 = 511 - y
            add_block(prt, x2, y2, z, color, player_id, False, False)
        if not prt.map.get_solid(x, y, z):
            block_action = BlockAction()
            block_action.player_id = player_id
            block_action.value = BUILD_BLOCK
            block_action.x = x
            block_action.y = y
            block_action.z = z
            prt.send_contained(block_action)
            prt.map.set_point(x, y, z, get_color_tuple(color))

def remove_block(prt, x, y, z, mirror_x = False, mirror_y = False):
    if x >= 0 and x < 512 and y >= 0 and y < 512 and z >= 0 and z < 64:
        if mirror_x == True or mirror_y == True:
            x2 = x
            y2 = y
            if mirror_x == True:
                x2 = 511 - x
            if mirror_y == True:
                y2 = 511 - y
            remove_block(prt, x2, y2, z, False, False)
        if prt.map.get_solid(x, y, z):
            block_action = BlockAction()
            block_action.player_id = 32
            block_action.value = DESTROY_BLOCK
            block_action.x = x
            block_action.y = y
            block_action.z = z
            prt.map.remove_point(x, y, z)
            prt.send_contained(block_action)
            return True
    return False

def mirror(connection, mirror_x, mirror_y):
    connection.mirror_x = bool(mirror_x)
    connection.mirror_y = bool(mirror_y)

add(mirror)

def tunnel(*arguments):
    connection = arguments[0]
    connection.reset_build()
    connection.callback = tunnel_r
    connection.arguments = arguments
    connection.select = True
    connection.points = 1

add(tunnel)

def tunnel_r(connection, radius, length, zoffset = 0):
    radius = int(radius)
    length = int(length)
    zoffset = int(zoffset)
    facing = connection.get_direction()
    if facing == WEST or facing == NORTH:
        length = -length
    for rel_h in xrange(-radius, radius + 1):
        for rel_v in xrange(-radius, 1):
            if round(sqrt(rel_h**2 + rel_v**2)) <= radius:
                if facing == NORTH or facing == SOUTH:
                    y1 = connection.block1_y
                    y2 = connection.block1_y + length
                    for y in xrange(min(y1, y2), max(y1, y2) + 1):
                        remove_block(connection.protocol, connection.block1_x + rel_h, y, connection.block1_z + rel_v + zoffset, connection.mirror_x, connection.mirror_y)
                elif facing == WEST or facing == EAST:
                    x1 = connection.block1_x
                    x2 = connection.block1_x + length
                    for x in xrange(min(x1, x2), max(x1, x2) + 1):
                        remove_block(connection.protocol, x, connection.block1_y + rel_h, connection.block1_z + rel_v + zoffset, connection.mirror_x, connection.mirror_y)

def insert(*arguments):
    connection = arguments[0]
    connection.reset_build()
    connection.callback = insert_r
    connection.arguments = arguments
    connection.select = True
    connection.points = 2

add(insert)

def insert_r(connection):
    x1 = min(connection.block1_x, connection.block2_x)
    x2 = max(connection.block1_x, connection.block2_x)
    y1 = min(connection.block1_y, connection.block2_y)
    y2 = max(connection.block1_y, connection.block2_y)
    z1 = min(connection.block1_z, connection.block2_z)
    z2 = max(connection.block1_z, connection.block2_z)
    color = make_color_tuple(connection.color)
    for xx in xrange(x1, x2 + 1):
        for yy in xrange(y1, y2 + 1):
            for zz in xrange(z1, z2 + 1):
                add_block(connection.protocol, xx, yy, zz, color, connection.player_id, connection.mirror_x, connection.mirror_y)

def delete(*arguments):
    connection = arguments[0]
    connection.reset_build()
    connection.callback = delete_r
    connection.arguments = arguments
    connection.select = True
    connection.points = 2

add(delete)

def delete_r(connection):
    x1 = min(connection.block1_x, connection.block2_x)
    x2 = max(connection.block1_x, connection.block2_x)
    y1 = min(connection.block1_y, connection.block2_y)
    y2 = max(connection.block1_y, connection.block2_y)
    z1 = min(connection.block1_z, connection.block2_z)
    z2 = max(connection.block1_z, connection.block2_z)
    for xx in xrange(x1, x2 + 1):
        for yy in xrange(y1, y2 + 1):
            for zz in xrange(z1, z2 + 1):
                remove_block(connection.protocol, xx, yy, zz, connection.mirror_x, connection.mirror_y)

def pattern(*arguments):
    connection = arguments[0]
    connection.reset_build()
    connection.callback = pattern_r
    connection.arguments = arguments
    connection.select = True
    connection.points = 2

add(pattern)

def pattern_r(connection, copies):
    copies = int(copies)
    x1 = min(connection.block1_x, connection.block2_x)
    x2 = max(connection.block1_x, connection.block2_x)
    y1 = min(connection.block1_y, connection.block2_y)
    y2 = max(connection.block1_y, connection.block2_y)
    z1 = min(connection.block1_z, connection.block2_z)
    z2 = max(connection.block1_z, connection.block2_z)
    delta_z = (z2 - z1) + 1
    for xx in xrange(x1, x2 + 1):
        for yy in xrange(y1, y2 + 1):
            for zz in xrange(z1, z2 + 1):
                if connection.protocol.map.get_solid(xx, yy, zz):
                    color = make_color_tuple(connection.protocol.map.get_point(xx, yy, zz)[1])
                    set_color(connection.protocol, color, 32)
                    for i in xrange(1, copies + 1):
                        z_offset = delta_z * i
                        add_block(connection.protocol, xx, yy, zz - z_offset, color, 32, connection.mirror_x, connection.mirror_y)

def hollow(*arguments):
    connection = arguments[0]
    connection.reset_build()
    connection.callback = hollow_r
    connection.arguments = arguments
    connection.select = True
    connection.points = 2

add(hollow)

def hollow_r(connection, thickness = 1):
    m = connection.protocol.map
    thickness = int(thickness) - 1
    x1 = min(connection.block1_x, connection.block2_x)
    x2 = max(connection.block1_x, connection.block2_x)
    y1 = min(connection.block1_y, connection.block2_y)
    y2 = max(connection.block1_y, connection.block2_y)
    z1 = min(connection.block1_z, connection.block2_z)
    z2 = max(connection.block1_z, connection.block2_z)
    blocks = []
    xr = x2 - x1 + 1
    yr = y2 - y1 + 1
    zr = z2 - z1 + 1
    for x in xrange(0, xr):
        blocks.append([])
        for y in xrange(0, yr):
            blocks[x].append([])
            for z in xrange(0, zr):
                blocks[x][y].append(False)
    def hollow_check(xc, yc, zc, thickness):
        if thickness > 0:
            for xx in xrange(xc - 1, xc + 2):
                if xx >= 0 and xx < xr:
                    for yy in xrange(yc - 1, yc + 2):
                        if yy >= 0 and yy < yr:
                            for zz in xrange(zc - 1, zc + 2):
                                if zz >= 0 and zz < zr:
                                    blocks[xx][yy][zz] = True
                                    if m.get_solid(x1 + xx, y1 + yy, z1 + zz):
                                        hollow_check(xx, yy, zz, thickness - 1)
    for x in xrange(0, xr):
        for y in xrange(0, yr):
            for z in xrange(0, zr):
                if m.get_solid(x1 + x, y1 + y, z1 + z):
                    if m.is_surface(x1 + x, y1 + y, z1 + z):
                        blocks[x][y][z] = True
                        hollow_check(x, y, z, thickness)
                else:
                    blocks[x][y][z] = True
    for x in xrange(0, xr):
        for y in xrange(0, yr):
            for z in xrange(0, zr):
                if not blocks[x][y][z]:
                    remove_block(connection.protocol, x1 + x, y1 + y, z1 + z)

def apply_script(protocol, connection, config):
    class MapMakingToolsConnection(connection):
        select = False
        mirror_x = False
        mirror_y = False

        def reset_build(self):
            self.block1_x = None
            self.block1_y = None
            self.block1_z = None
            self.block2_x = None
            self.block2_y = None
            self.block2_z = None
            self.callback = None
            self.arguments = None
            self.select = False
            self.points = None

        def get_direction(self):
            orientation = self.world_object.orientation
            angle = atan2(orientation.y, orientation.x)
            if angle < 0:
                angle += 6.283185307179586476925286766559
            # Convert to units of quadrents
            angle *= 0.63661977236758134307553505349006
            angle = round(angle)
            if angle == 4:
                angle = 0
            return angle

        def on_block_destroy(self, x, y, z, value):
            if self.select == True:
                if self.points == 1:
                    self.block1_x = x
                    self.block1_y = y
                    self.block1_z = z
                    self.callback(*self.arguments)
                    self.reset_build()
                    return False
                elif self.points == 2:
                    if self.block1_x == None:
                        self.block1_x = x
                        self.block1_y = y
                        self.block1_z = z
                        self.send_chat('First block selected')
                        return False
                    else:
                        if not (x == self.block1_x and y == self.block1_y and z == self.block1_z):
                            self.block2_x = x
                            self.block2_y = y
                            self.block2_z = z
                            self.callback(*self.arguments)
                            self.reset_build()
                            self.send_chat('Second block selected')
                            return False
            if self.mirror_x == True or self.mirror_y == True:
                x2 = x
                y2 = y
                if self.mirror_x == True:
                    x2 = 511 - x
                if self.mirror_y == True:
                    y2 = 511 - y
                remove_block(self.protocol, x2, y2, z)
            connection.on_block_destroy(self, x, y, z, value)

        def on_block_build(self, x, y, z):
            if self.mirror_x == True or self.mirror_y == True:
                x2 = x
                y2 = y
                if self.mirror_x == True:
                    x2 = 511 - x
                if self.mirror_y == True:
                    y2 = 511 - y
                add_block(self.protocol, x2, y2, z, make_color_tuple(self.color), self.player_id)
            connection.on_block_build(self, x, y, z)

    return protocol, MapMakingToolsConnection
