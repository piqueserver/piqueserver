"""
/rapid [player] will put the player in rapid mode, speeding up all tools
including weapons.

If any of DEFAULT_RAPID_BLOCKS, DEFAULT_RAPID_WEAPONS or DEFAULT_RAPID_SPADE
are set to True, rapid hack detection will be disabled for everyone.

RAPID_BLOCK_DELAY determines how fast block placement should be.
Lowering this value is not recommended except for local use. Ping to the server
is the effective lower limit: if this value is set to 0.1 (0.1 seconds = 100ms),
users with ping above that won't have the same advantage as the rest of the
players.

Mantainer: hompy
"""

from twisted.internet.reactor import callLater
from twisted.internet.task import LoopingCall
from pyspades.server import set_tool
from pyspades.constants import *
from commands import add, admin, get_player

RAPID_INTERVAL = 0.08
RAPID_BLOCK_DELAY = 0.26
DEFAULT_RAPID_BLOCKS = False
DEFAULT_RAPID_WEAPONS = False
DEFAULT_RAPID_SPADE = False

@admin
def rapid(connection, player = None):
    protocol = connection.protocol
    if player is not None:
        player = get_player(protocol, player)
    elif connection in protocol.players:
        player = connection
    else:
        raise ValueError()
    
    player.rapid = not player.rapid
    if player.rapid:
        player.rapid_blocks = player.rapid_weapons = player.rapid_spade = True
    else:
        player.rapid_blocks = DEFAULT_RAPID_BLOCKS
        player.rapid_weapons = DEFAULT_RAPID_WEAPONS
        player.rapid_spade = DEFAULT_RAPID_SPADE
    player.rapid_hack_detect = not (player.rapid_blocks or
        player.rapid_weapons or player.rapid_spade)
    
    message = 'now rapid' if player.rapid else 'no longer rapid'
    player.send_chat("You're %s" % message)
    if connection is not player and connection in protocol.players:
        connection.send_chat('%s is %s' % (player.name, message))
    protocol.irc_say('* %s is %s' % (player.name, message))

def resend_tool(player):
    set_tool.player_id = player.player_id
    set_tool.value = player.tool
    if player.weapon_object.shoot:
        player.protocol.send_contained(set_tool)
    else:
        player.send_contained(set_tool)

add(rapid)

def apply_script(protocol, connection, config):
    class RapidConnection(connection):
        rapid = False
        rapid_loop = None
        rapid_blocks = False
        rapid_weapons = False
        rapid_spade = False
        
        def reset_rapid(self):
            self.rapid = False
            self.rapid_blocks = DEFAULT_RAPID_BLOCKS
            self.rapid_weapons = DEFAULT_RAPID_WEAPONS
            self.rapid_spade = DEFAULT_RAPID_SPADE
            self.rapid_hack_detect = not (self.rapid_blocks or
                self.rapid_weapons or self.rapid_spade)
        
        def on_connect(self):
            self.rapid_loop = LoopingCall(resend_tool, self)
            connection.on_connect(self)
        
        def on_reset(self):
            self.reset_rapid()
            connection.on_reset(self)
        
        def on_login(self, name):
            self.reset_rapid()
            connection.on_login(self, name)
        
        def on_disconnect(self):
            if self.rapid_loop and self.rapid_loop.running:
                self.rapid_loop.stop()
            self.rapid_loop = None
            connection.on_disconnect(self)
        
        def on_block_build(self, x, y, z):
            if self.rapid_blocks:
                delay = max(0.0, RAPID_BLOCK_DELAY - self.latency / 1000.0)
                if delay > 0.0:
                    callLater(delay, resend_tool, self)
                else:
                    resend_tool(self)
            connection.on_block_build(self, x, y, z)
        
        def on_grenade_thrown(self, grenade):
            if self.rapid_weapons:
                resend_tool(self)
            connection.on_grenade_thrown(self, grenade)
        
        def on_shoot_set(self, fire):
            if self.rapid_loop and (
                (self.rapid_spade and self.tool == SPADE_TOOL) or
                (self.rapid_weapons and self.tool == WEAPON_TOOL)):
                if not self.rapid_loop.running and fire:
                    self.rapid_loop.start(RAPID_INTERVAL)
                elif self.rapid_loop.running and not fire:
                    self.rapid_loop.stop()
            connection.on_shoot_set(self, fire)
    
    return protocol, RapidConnection