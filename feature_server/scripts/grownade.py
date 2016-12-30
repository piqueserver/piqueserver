"""
Turns your grenades into magical kv6-growing seeds. Or beans!

Use /model <filename> to load model files. These must be placed inside a folder
named 'kv6' in the feature_server directory. A full path would look like this:
"C:\my_pyspades\feature_server\kv6\some_model.kv6". Then you load it with
/model some_model

Wildcards and subfolders are allowed. Some examples:

/model building*
Loads all models that start with "building", like "building1" and "buildingred"

/model my_trees/*
Loads all models inside a folder named "my_trees"

When you have many models loaded, each grenade will pick a random one to grow.
To stop littering the map with random objects just type /model again.

---

THE PIVOT POINT in kv6 files determines the first block to be placed. The rest
of the model will then follow, growing around it.

The pivot point MUST be sitting on a block, or the model won't load. Checking
'Adjust pivots' in the Tools menu in SLAB6 will show handy coordinates.
To be sure, you can move the pivot to *half* of a block, e.g.: (4.50, 4.50, 8.50)

In a tree kv6, for example, the pivot point would lie on the lowest block of the
tree trunk, so that it grows up and not into the ground.

---

You can adjust FLYING_MODELS and GROW_ON_WATER to allow growing in the air and
on water, respectively. These are disabled by default so you can fly high and
sprinkle tree-growing grenades without worrying about unseemly oddities.

Maintainer: hompy
"""

import os
from glob import glob
from struct import unpack
from random import choice
from itertools import product
from collections import deque, namedtuple
from twisted.internet.reactor import seconds
from twisted.internet.task import LoopingCall
from pyspades.server import block_action, block_line, set_color
from pyspades.common import make_color
from pyspades.constants import *
from commands import add, admin, name, get_player

FLYING_MODELS = False # if False grenades exploding in midair will be ignored
GROW_ON_WATER = False # if False grenades exploding in water will do nothing

KV6_DIR = './kv6'
LOWEST_Z = 63 if GROW_ON_WATER else 62
GROW_INTERVAL = 0.3

S_NO_KV6_FOLDER = "You haven't created a kv6 folder yet!"
S_NO_MATCHES = "Couldn't find any model files matching {expression}"
S_LOADED_SINGLE = 'Loaded model {filename}'
S_LOADED = 'Loaded {filenames}. Each grenade will pick one at random'
S_FAILED = 'Failed to load {filenames}'
S_PIVOT_TIP = 'Make sure the pivot points are correctly placed'
S_CANCEL = 'No longer spawning models'
S_SPECIFY_FILES = 'Specify model files to load. Wildcards are allowed, ' \
    'e.g.: "bunker", "tree*"'

@name('model')
@admin
def model_grenades(connection, expression = None):
    protocol = connection.protocol
    if connection not in protocol.players:
        raise ValueError()
    player = connection

    result = None
    if expression:
        if not os.path.isdir(KV6_DIR):
            return S_NO_KV6_FOLDER
        if not os.path.splitext(expression)[-1]:
            # append default extension
            expression += '.kv6'
        paths = glob(os.path.join(KV6_DIR, expression))
        if not paths:
            return S_NO_MATCHES.format(expression = expression)

        # attempt to load models, discard invalid ones
        models, loaded, failed = [], [], []
        for path in paths:
            model = KV6Model(path)
            filename = os.path.split(path)[-1]
            if model.voxels:
                models.append(model)
                loaded.append(filename)
            else:
                failed.append(filename)
        if len(loaded) == 1:
            result = S_LOADED_SINGLE.format(filename = loaded[0])
        elif len(loaded) > 1:
            result = S_LOADED.format(filenames = ', '.join(loaded))
        if failed:
            player.send_chat(S_FAILED.format(filenames = ', '.join(failed)))
            player.send_chat(S_PIVOT_TIP)

        if models:
            player.grenade_models = models
    elif player.grenade_models:
        player.grenade_models = None
        result = S_CANCEL
    else:
        result = S_SPECIFY_FILES
    if result:
        player.send_chat(result)

add(model_grenades)

KV6Voxel = namedtuple('KV6Voxel', 'b g r a z neighbors normal_index')
NonSurfaceKV6Voxel = KV6Voxel(40, 64, 103, 128, 0, 0, 0)

class KV6Model:
    """
    Custom implementation that also generates non-surface voxels.
    Not suitable for general purpose.
    """

    size = None
    pivot = None
    voxels = None

    def __init__(self, path):
        with open(path, 'rb') as file:
            file.read(4) # 'Kvxl'

            self.size = unpack('III', file.read(4 * 3))
            self.pivot = tuple(int(n) for n in unpack('fff', file.read(4 * 3)))

            voxel_count, = unpack('I', file.read(4))
            voxels = []
            for i in xrange(voxel_count):
                voxel = KV6Voxel._make(unpack('BBBBHBB', file.read(8)))
                voxels.append(voxel)

            size_x, size_y, size_z = self.size
            file.read(4 * size_x) # discard extra information

            voxel_map = {}
            voxel_iter = iter(voxels)
            for x, y in product(xrange(size_x), xrange(size_y)):
                last_z = None
                column_len, = unpack('H', file.read(2))
                for i in xrange(column_len):
                    voxel = next(voxel_iter)
                    voxel_map[(x, y, voxel.z)] = voxel
                    if last_z is not None and not voxel.neighbors & 0b00010000:
                        for z in xrange(last_z + 1, voxel.z):
                            inside_voxel = NonSurfaceKV6Voxel._replace(z = z)
                            voxel_map[(x, y, z)] = inside_voxel
                    last_z = voxel.z

            if self.pivot not in voxel_map:
                return
            self.voxels = voxel_map

class BuildQueue:
    interval = 0.02
    blocks_per_cycle = 3
    blocks = None
    loop = None
    call_on_exhaustion = None

    def __init__(self, protocol, call_on_exhaustion = None):
        self.protocol = protocol
        self.blocks = deque()
        self.loop = LoopingCall(self.cycle)
        self.loop.start(self.interval)
        self.call_on_exhaustion = call_on_exhaustion

    def cycle(self):
        if not self.blocks:
            self.loop.stop()
            if self.call_on_exhaustion:
                self.call_on_exhaustion()
            return
        blocks_left = self.blocks_per_cycle
        last_color = None
        while self.blocks and blocks_left:
            x, y, z, color = self.blocks.popleft()
            if color != last_color:
                set_color.value = make_color(*color)
                set_color.player_id = 32
                self.protocol.send_contained(set_color, save = True)
                last_color = color
            if not self.protocol.map.get_solid(x, y, z):
                block_action.value = BUILD_BLOCK
                block_action.player_id = 32
                block_action.x = x
                block_action.y = y
                block_action.z = z
                self.protocol.send_contained(block_action, save = True)
                self.protocol.map.set_point(x, y, z, color)
                blocks_left -= 1
        self.protocol.update_entities()

    def push_block(self, x, y, z, color):
        if not self.loop.running:
            self.loop.start(self.interval)
        self.blocks.append((x, y, z, color))

class GrowModel:
    model = None
    x, y, z = None, None, None
    open, closed = None, None
    build_queue = None
    grow_loop = None

    def __init__(self, protocol, model, x, y, z):
        self.protocol = protocol
        self.model = model
        self.x, self.y, self.z = x, y, z
        self.open = [model.pivot]
        self.closed = set()
        self.build_queue = BuildQueue(protocol, self.queue_exhausted)
        self.grow_loop = LoopingCall(self.grow_cycle)
        self.grow_loop.start(GROW_INTERVAL)

    def grow_cycle(self):
        new_nodes = set()
        for xyz in self.open:
            if xyz not in self.model.voxels or xyz in self.closed:
                continue
            self.closed.add(xyz)
            x, y, z = xyz
            new_nodes.add((x, y, z - 1))
            new_nodes.add((x, y, z + 1))
            new_nodes.add((x, y - 1, z))
            new_nodes.add((x, y + 1, z))
            new_nodes.add((x - 1, y, z))
            new_nodes.add((x + 1, y, z))
            p_x, p_y, p_z = self.model.pivot
            x, y, z = x + self.x - p_x, y + self.y - p_y, z + self.z - p_z
            if x < 0 or y < 0 or z < 0 or x >= 512 or y >= 512 or z >= LOWEST_Z:
                continue
            voxel = self.model.voxels[xyz]
            self.build_queue.push_block(x, y, z, (voxel.r, voxel.g, voxel.b))
        self.open = new_nodes
        if not new_nodes:
            self.grow_loop.stop()

    def queue_exhausted(self):
        if not self.open:
            self.release()

    def release(self):
        if self.build_queue.loop.running:
            self.build_queue.loop.stop()
        self.build_queue.loop = None
        if self.grow_loop.running:
            self.grow_loop.stop()
        self.grow_loop = None
        self.protocol.growers.remove(self)

def apply_script(protocol, connection, config):
    class SeedyConnection(connection):
        grenade_models = None

        def on_reset(self):
            self.grenade_models = None
            connection.on_reset(self)

        def on_grenade_thrown(self, grenade):
            if self.grenade_models:
                grenade.name = 'seed'
                grenade.callback = self.seed_exploded
            connection.on_grenade_thrown(self, grenade)

        def seed_exploded(self, grenade):
            if not self.grenade_models:
                return
            x, y, z = (int(n) for n in grenade.position.get())
            map = self.protocol.map
            if (not FLYING_MODELS and not map.get_solid(x, y, z + 1) and
                not z == LOWEST_Z == 63):
                return
            model = choice(self.grenade_models)
            grower = GrowModel(self.protocol, model, x, y, z)
            self.protocol.growers.append(grower)

    class SeedyProtocol(protocol):
        growers = None

        def on_map_change(self, map):
            self.growers = []
            protocol.on_map_change(self, map)

        def on_map_leave(self):
            for grower in self.growers[:]:
                grower.release()
            self.growers = None
            protocol.on_map_leave(self)

    return SeedyProtocol, SeedyConnection
