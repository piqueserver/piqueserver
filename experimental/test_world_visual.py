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

import sys
sys.path.append('..')

from pyspades.common import *
from pyspades.vxl import VXLData, get_color_tuple
from pyspades import world
import pyglet
from pyglet.window import key
import math
from pyglet.gl import *

fp = None
for name in ('../feature_server/maps/pyspades.vxl', 
             './feature_server/maps/pyspades.vxl'):
    try:
        fp = open(name, 'rb')
    except IOError:
        pass

if fp is None:
    raise SystemExit('no map file found')

map = VXLData(fp)
fp.close()

def on_fall(damage):
    print 'on fall:', damage

new_world = world.World()
new_world.map = map
character = new_world.create_object(world.Character,
    Vertex3(20.0, 20.0, 5.0), Vertex3(0.999992012978, 0.0, -0.00399998947978),
    on_fall)

window = pyglet.window.Window(width = 600, height = 600,
    resizable=True)

keyboard = key.KeyStateHandler()
window.set_handlers(keyboard)

def draw_quad(x1, y1, x2, y2, color = (255, 255, 255)):
    r, g, b = color
    glColor4ub(r, g, b, 255)
    glBegin(GL_QUADS)
    glVertex2f(x1, y1)
    glVertex2f(x2, y1)
    glVertex2f(x2, y2)
    glVertex2f(x1, y2)
    glEnd()

scale = 50.0

def get_position(x_orig, y_orig, z_orig):
    x = ((x_orig) / scale) * 600
    y = ((-z_orig) / scale) * 600
    return x, y

def draw_block(x, y, z, color):
    x1, y1 = get_position(x, y, z)
    x2, y2 = get_position(x + 1, y + 1, z + 1)
    draw_quad(x1, y1, x2, y2, color)

class block_cache:
    blocks = []
    y = None

@window.event
def on_draw():
    glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
    glLoadIdentity()
    position = character.position
    glTranslatef((-position.x / scale) * 600 + 300, window.height + 200, 0)
    map_y = int(position.y)
    if block_cache.y != map_y:
        block_cache.blocks = block_list = []
        for x in xrange(512):
            for z in xrange(64):
                color = map.get_color(x, map_y, z)
                if color == 0:
                    continue
                r, g, b, a = get_color_tuple(color)
                block_list.append((x, z, (r, g, b)))
    for x, z, color in block_cache.blocks:
        draw_block(x, map_y, z, color)

    x, y = get_position(position.x, position.y, position.z)
    add_height = 0
    if not character.crouch:
        add_height = (0.9 / scale) * 600
    draw_quad(x - 2, y - 12 - add_height, x + 2, y + 5)
    for item in new_world.objects:
        if item.name != 'grenade':
            continue
        position = item.position
        x, y = get_position(position.x, position.y, position.z)
        pad = 2
        draw_quad(x - pad, y - pad, x + pad, y + pad)

def on_nade(nade):
    damage = nade.get_damage(character.position)
    if damage is None:
        return
    print 'nade damage:', damage

def on_key_press(symbol, modifiers):
    if symbol == key.SPACE:
        character.jump = True
    elif symbol == key.F:
        character.throw_grenade(5, on_nade)
    elif symbol == key.X:
        new_world.update(1 / (60.0 * 2))

window.push_handlers(
    on_key_press = on_key_press)

def update(dt):
    if not keyboard[key.C]:
        character.set_walk(
            keyboard[key.RIGHT],
            keyboard[key.LEFT],
            keyboard[key.UP],
            keyboard[key.DOWN]
        )
        character.set_crouch(keyboard[key.Z])
        new_world.update(dt)

# setup :)

pyglet.clock.schedule_interval(update, 1 / 60.0)

pyglet.app.run()