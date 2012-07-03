"""
Blocks built by players are twice as hard to break.

Maintainer: hompy
"""

from pyspades.server import block_action, set_color
from pyspades.common import make_color
from pyspades.constants import *

def rebuild_block(player, x, y, z, color):
    set_color.value = color
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

def apply_script(protocol, connection, config):
    class StrongBlockConnection(connection):
        def on_block_build(self, x, y, z):
            self.protocol.strong_blocks[(x, y, z)] = make_color(*self.color)
            connection.on_block_build(self, x, y, z)
        
        def on_line_build(self, points):
            raw_color = make_color(*self.color)
            for xyz in points:
                self.protocol.strong_blocks[xyz] = raw_color
            connection.on_line_build(self, points)
        
        def on_block_destroy(self, x, y, z, value):
            xyz = (x, y, z)
            can_destroy = connection.on_block_destroy(self, x, y, z, value)
            if can_destroy != False and xyz in self.protocol.strong_blocks:
                color = self.protocol.strong_blocks.pop(xyz)
                rebuild_block(self, x, y, z, color)
                return False
            return can_destroy
    
    class StrongBlockProtocol(protocol):
        strong_blocks = None
        
        def on_map_change(self, map):
            self.strong_blocks = {}
            protocol.on_map_change(self, map)
    
    return StrongBlockProtocol, StrongBlockConnection