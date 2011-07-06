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
    Vertex3(20.0, 20.0, 5.0), Vertex3(0.999992012978, 0.0, -0.00399998947978))

config = Config(sample_buffers=1, samples=4, 
                depth_size=16, double_buffer=True)
window = pyglet.window.Window(width = 600, height = 600,
    resizable=True, config=config)

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

@window.event
def on_draw():
    glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
    glLoadIdentity()
    glTranslatef(0, window.height, 0)
    position = character.position
    map_y = int(position.y)
    x = ((position.x) / 32.0) * window.width
    y = ((-position.z) / 64.0) * window.height
    draw_quad(x - 5, y - 5, x + 5, y + 5)
    for x in xrange(512):
        for z in xrange(64):
            r, g, b, a = map.get_color(x, map_y, z)
            if color == 0:
                continue
            
            draw_quad()

def on_key_press(symbol, modifiers):
    if symbol == key.SPACE:
        character.set_animation(False, True, False, False)

window.push_handlers(
    on_key_press = on_key_press)

def update(dt):
    character.set_walk(
        keyboard[key.UP],
        keyboard[key.DOWN],
        keyboard[key.LEFT],
        keyboard[key.RIGHT]
    )
    new_world.update(dt)
    # print 'framerate:', 1 / dt

# setup :)

pyglet.clock.schedule_interval(update, 1 / 60.0)

pyglet.app.run()