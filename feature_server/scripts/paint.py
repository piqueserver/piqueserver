"""
Lets you change the color of the block you are looking at.
/paint [player] enables painting mode for the player.

With block tool selected, pick a color, then hold down sneak key
(<V> by default) to paint.

Maintainer: hompy
"""

from pyspades.server import block_action
from pyspades.common import Vertex3
from pyspades.constants import *
from commands import add, admin, get_player

PAINT_RAY_LENGTH = 32.0

@admin
def paint(connection, player = None):
    protocol = connection.protocol
    if player is not None:
        player = get_player(protocol, player)
    elif connection in protocol.players:
        player = connection
    else:
        raise ValueError()

    player.painting = not player.painting

    message = 'now painting' if player.painting else 'no longer painting'
    player.send_chat("You're %s" % message)
    if connection is not player and connection in protocol.players:
        connection.send_chat('%s is %s' % (player.name, message))
    protocol.irc_say('* %s is %s' % (player.name, message))

add(paint)

def paint_block(protocol, player, x, y, z, color):
    if x < 0 or y < 0 or z < 0 or x >= 512 or y >= 512 or z >= 62:
        return False
    if protocol.map.get_color(x, y, z) == color:
        return False
    protocol.map.set_point(x, y, z, color)
    block_action.x = x
    block_action.y = y
    block_action.z = z
    block_action.player_id = player.player_id
    block_action.value = DESTROY_BLOCK
    protocol.send_contained(block_action, save = True)
    block_action.value = BUILD_BLOCK
    protocol.send_contained(block_action, save = True)
    return True

def paint_ray(player):
    if player.tool != BLOCK_TOOL:
        return
    location = player.world_object.cast_ray(PAINT_RAY_LENGTH)
    if location:
        x, y, z = location
        if player.on_block_build_attempt(x, y, z) == False:
            return
        paint_block(player.protocol, player, x, y, z, player.color)

def apply_script(protocol, connection, config):
    class PaintConnection(connection):
        painting = False

        def on_reset(self):
            self.painting = False
            connection.on_reset(self)

        def on_position_update(self):
            if self.painting and self.world_object.sneak:
                paint_ray(self)
            connection.on_position_update(self)

        def on_orientation_update(self, x, y, z):
            if self.painting and self.world_object.sneak:
                paint_ray(self)
            connection.on_orientation_update(self, x, y, z)

        def on_animation_update(self, jump, crouch, sneak, sprint):
            if self.painting and sneak:
                paint_ray(self)
            return connection.on_animation_update(self, jump, crouch, sneak, sprint)

    return protocol, PaintConnection
