"""
Blocks built by players are twice as hard to break.

* You can remove your own blocks as if they weren't strong.
* Dirt-colored or buried blocks (those that turn into dirt) become normal blocks.

Maintainer: hompy
"""

from collections import namedtuple
from pyspades.server import block_action, set_color
from pyspades.common import make_color
from pyspades.color import rgb_distance
from pyspades.constants import *

DIRT_COLOR = (71, 48, 35)

StrongBlock = namedtuple('StrongBlock', 'color owner')

def rebuild_block(player, x, y, z, color):
    set_color.value = make_color(*color)
    set_color.player_id = 32
    block_action.player_id = 32
    block_action.x = x
    block_action.y = y
    block_action.z = z
    block_action.value = DESTROY_BLOCK
    player.send_contained(block_action)
    block_action.value = BUILD_BLOCK
    player.send_contained(set_color)
    player.send_contained(block_action)

def check_if_buried(protocol, x, y, z):
    if not protocol.map.is_surface(x, y, z):
        protocol.strong_blocks.pop((x, y, z), None)

def bury_adjacent(protocol, x, y, z):
    check_if_buried(protocol, x, y, z - 1)
    check_if_buried(protocol, x, y, z + 1)
    check_if_buried(protocol, x - 1, y, z)
    check_if_buried(protocol, x + 1, y, z)
    check_if_buried(protocol, x, y - 1, z)
    check_if_buried(protocol, x, y + 1, z)

def is_color_dirt(color):
    return rgb_distance(color, DIRT_COLOR) < 30

def apply_script(protocol, connection, config):
    class StrongBlockConnection(connection):
        def on_disconnect(self):
            strong_blocks = self.protocol.strong_blocks
            for xyz, strong_block in strong_blocks.iteritems():
                if strong_block.owner is self:
                    strong_blocks[xyz] = strong_block._replace(owner = None)
            connection.on_disconnect(self)
        
        def on_block_build(self, x, y, z):
            if not is_color_dirt(self.color):
                strong_block = StrongBlock(self.color, self)
                self.protocol.strong_blocks[(x, y, z)] = strong_block
                bury_adjacent(self.protocol, x, y, z)
            connection.on_block_build(self, x, y, z)
        
        def on_line_build(self, points):
            if not is_color_dirt(self.color):
                strong_block = StrongBlock(self.color, self)
                for xyz in points:
                    self.protocol.strong_blocks[xyz] = strong_block
                    bury_adjacent(self.protocol, *xyz)
            connection.on_line_build(self, points)
        
        def on_block_destroy(self, x, y, z, value):
            can_destroy = connection.on_block_destroy(self, x, y, z, value)
            if can_destroy != False:
                strong_block = self.protocol.strong_blocks.pop((x, y, z), None)
                if strong_block is not None:
                    # block is a strong block
                    if strong_block.owner is not self:
                        # tough for everyone but the player who built it
                        rebuild_block(self, x, y, z, strong_block.color)
                        return False
            return can_destroy
    
    class StrongBlockProtocol(protocol):
        strong_blocks = None
        
        def on_map_change(self, map):
            self.strong_blocks = {}
            protocol.on_map_change(self, map)
    
    return StrongBlockProtocol, StrongBlockConnection