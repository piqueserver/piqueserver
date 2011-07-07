from pyspades.common import *
from pyspades.load import VXLData, get_color_tuple
import world
import pyglet
from pyglet.window import key
import math
from pyglet.gl import *

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

scale = 64.0

def get_position(x_orig, y_orig, z_orig):
    x = ((x_orig) / scale) * 600
    y = ((-z_orig) / scale) * 600
    return x, y

def draw_block(x, y, z, color):
    x1, y1 = get_position(x, y, z)
    x2, y2 = get_position(x + 1, y + 1, z + 1)
    draw_quad(x1, y1, x2, y2, color)

block_cache = {}

@window.event
def on_draw():
    glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
    glLoadIdentity()
    glTranslatef(0, window.height, 0)
    position = character.position
    map_y = int(position.y + 0.5)
    if map_y not in block_cache:
        block_cache[map_y] = block_list = []
        for x in xrange(512):
            for z in xrange(64):
                color = map.get_color(x, map_y, z)
                if color == 0:
                    continue
                r, g, b, a = get_color_tuple(color)
                block_list.append((x, z, (r, g, b)))
    x, y = get_position(position.x, position.y, character.guess_z)
    add_height = 0
    if not character.crouch:
        add_height = (0.9 / scale) * 600
    draw_quad(x - 2, y - 12 - add_height, x + 2, y + 5)
    for x, z, color in block_cache[map_y]:
        draw_block(x, map_y, z, color)

def on_key_press(symbol, modifiers):
    if symbol == key.SPACE:
        character.set_animation(jump = True)

window.push_handlers(
    on_key_press = on_key_press)

def update(dt):
    character.set_walk(
        keyboard[key.RIGHT],
        keyboard[key.LEFT],
        keyboard[key.UP],
        keyboard[key.DOWN]
    )
    character.set_animation(
        crouch = keyboard[key.Z]
    )
    position = character.position
    new_world.update(dt)

# setup :)

pyglet.clock.schedule_interval(update, 1 / 60.0)

pyglet.app.run()