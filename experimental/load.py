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

import pyglet
from pyglet.window import key
import math

from pyspades.load import VXLData

data = VXLData(open('..\lastsav.vxl', 'rb'))

from pyglet.gl import *

config = Config(sample_buffers=1, samples=4, 
                depth_size=16, double_buffer=True)
window = pyglet.window.Window(resizable=True, config=config)
window.set_exclusive_mouse(True)

rquad = 0.0

glEnable(GL_DEPTH_TEST)
glEnable(GL_CULL_FACE)
glClearColor(0.0, 1.0, 1.0, 1.0)
glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
glTexEnvf(GL_TEXTURE_ENV, GL_TEXTURE_ENV_MODE, GL_MODULATE)
glEnable(GL_BLEND)

keyboard = key.KeyStateHandler()

window.set_handlers(keyboard)

class Camera(object):
    TRAVEL_SPEED = 5

    x = y = z = 0
    r_x = r_y = r_z = 0
    view_x = view_y = view_z = 0
    def __init__(self):
        pass
    
    def add_mouse_motion(self, dx, dy):
        self.r_x += dy
        self.r_y += -dx
        val1 = math.cos(math.radians(self.r_y + 90.0))
        val2 = -math.sin(math.radians(self.r_y + 90.0))
        cosX = math.cos(math.radians(self.r_x))
        self.view_x = val1 * cosX
        self.view_z = val2 * cosX
        self.view_y = math.sin(math.radians(self.r_x))
    
    def transform(self):
        glRotatef(-self.r_x, 1.0, 0.0, 0.0)
        glRotatef(-self.r_y, 0.0, 1.0, 0.0)
        glRotatef(-self.r_z, 0.0, 0.0, 1.0)
        glTranslatef(self.x, self.y, self.z)
    
    def update(self, dt):
        speed = self.TRAVEL_SPEED * dt
        if keyboard[key.UP]:
            self.x += self.view_x * -speed
            self.y += self.view_y * -speed
            self.z += self.view_z * -speed
        if keyboard[key.DOWN]:
            self.x += self.view_x * speed
            self.y += self.view_y * speed
            self.z += self.view_z * speed
        if keyboard[key.LEFT]:
            self.x += self.view_z * -speed
            self.z += -self.view_x * -speed
        if keyboard[key.RIGHT]:
            self.x += self.view_z * speed
            self.z += -self.view_x * speed

camera = Camera()

@window.event
def on_resize(width, height):
    # Override the default on_resize handler to create a 3D projection
    glViewport(0, 0, width, height)
    glMatrixMode(GL_PROJECTION)
    glLoadIdentity()
    gluPerspective(60., width / float(height), .1, 1000.)
    glMatrixMode(GL_MODELVIEW)
    
    return pyglet.event.EVENT_HANDLED

@window.event
def on_mouse_motion(x, y, dx, dy):
    camera.add_mouse_motion(dx, dy)

@window.event
def on_draw():
    glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
    glLoadIdentity()
    
    camera.transform()
    
    cubes.draw()

def update(dt):
    print 'fps:', 1 / dt
    camera.update(dt)

# setup :)

cubes = pyglet.graphics.Batch()

for x_origin in xrange(0, 200):
    for y_origin in xrange(0, 200):
        for z_origin in xrange(0, 30):
            solid, color = data.get_point(x_origin, y_origin, z_origin)
            if not solid or color[-1] == 0:
                continue
            z = y_origin
            y = -z_origin
            x = x_origin
            cubes.add(24, GL_QUADS, None,
                ('v3f', (
                    x + 0.5, y + 0.5, z - 0.5,
                    x - 0.5, y + 0.5, z - 0.5,
                    x - 0.5, y + 0.5, z + 0.5,
                    x + 0.5, y + 0.5, z + 0.5,
                    
                    x + 0.5, y - 0.5, z + 0.5,
                    x - 0.5, y - 0.5, z + 0.5,
                    x - 0.5, y - 0.5, z - 0.5,
                    x + 0.5, y - 0.5, z - 0.5,
                    
                    x + 0.5, y + 0.5, z + 0.5,
                    x - 0.5, y + 0.5, z + 0.5,
                    x - 0.5, y - 0.5, z + 0.5,
                    x + 0.5, y - 0.5, z + 0.5,
                    
                    x + 0.5, y - 0.5, z - 0.5,
                    x - 0.5, y - 0.5, z - 0.5,
                    x - 0.5, y + 0.5, z - 0.5,
                    x + 0.5, y + 0.5, z - 0.5,
                    
                    x - 0.5, y + 0.5, z + 0.5,
                    x - 0.5, y + 0.5, z - 0.5,
                    x - 0.5, y - 0.5, z - 0.5,
                    x - 0.5, y - 0.5, z + 0.5,
                    
                    x + 0.5, y + 0.5, z - 0.5,
                    x + 0.5, y + 0.5, z + 0.5,
                    x + 0.5, y - 0.5, z + 0.5,
                    x + 0.5, y - 0.5, z - 0.5
                )), 
            ('c4B', color * 24))

pyglet.clock.schedule_interval(update, 1 / 85.0)

pyglet.app.run()