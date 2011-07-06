from pyspades.common import *
from pyspades.load import VXLData
import world
import pyglet
from pyglet.window import key
import math
from pyglet.gl import *
from render import Renderer

fp = None
for name in ('../data/sinc0.vxl', './data/sinc0.vxl'):
    try:
        fp = open(name, 'rb')
    except IOError:
        pass

if fp is None:
    raise SystemExit('no map file found')

map = VXLData(fp)
fp.close()

new_world = world.World(map)
character = new_world.create_object(world.Character,
    Vertex3(20.0, 20.0, 5.0), Vertex3())

config = Config(sample_buffers=1, samples=4, 
                depth_size=16, double_buffer=True)
window = pyglet.window.Window(width = 600, height = 600,
    resizable=True, config=config)

keyboard = key.KeyStateHandler()

window.set_handlers(keyboard)

@window.event
def on_draw():
    glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
    glLoadIdentity()
    glTranslatef(0, window.height, 0)
    position = character.position
    x = ((position.x) / 512.0) * window.width
    y = ((-position.z) / 64.0) * window.height
    
    glBegin(GL_QUADS)
    
    glVertex2f(x, y)
    glVertex2f(x + 10, y)
    glVertex2f(x + 10, y + 10)
    glVertex2f(x, y + 10)
    glEnd()

@window.event
def on_key_press(symbol, modifiers):
    if symbol == key.SPACE:
        print 'yay'

def update(dt):
    new_world.update(dt)
    print 'framerate:', 1 / dt

# setup :)

pyglet.clock.schedule_interval(update, 1 / 60.0)

pyglet.app.run()