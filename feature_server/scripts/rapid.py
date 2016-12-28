"""
/rapid [player] will put the player in rapid mode, speeding up all tools
including weapons.

RAPID_BLOCK_DELAY determines how fast block placement should be.
Lowering this value is not recommended except for local use. Ping to the server
is the effective lower limit: if this value is set to 0.1 (0.1 seconds = 100ms),
users with ping above that won't have the same advantage as the rest of the
players.

Set ALWAYS_RAPID to TRUE to automatically get rapid when you login.

Mantainer: hompy
"""

from twisted.internet.reactor import callLater
from twisted.internet.task import LoopingCall
from pyspades.server import set_tool
from pyspades.constants import *
from commands import add, admin, get_player, name

ALWAYS_RAPID = False
RAPID_INTERVAL = 0.08
RAPID_BLOCK_DELAY = 0.26

@name('rapid')
@admin
def toggle_rapid(connection, player = None):
    protocol = connection.protocol
    if player is not None:
        player = get_player(protocol, player)
    elif connection in protocol.players:
        player = connection
    else:
        raise ValueError()
    
    player.rapid = rapid = not player.rapid
    player.rapid_hack_detect = not rapid
    if rapid:
        player.rapid_loop = LoopingCall(resend_tool, player)
    else:
        if player.rapid_loop and player.rapid_loop.running:
            player.rapid_loop.stop()
        player.rapid_loop = None
    
    message = 'now rapid' if rapid else 'no longer rapid'
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

add(toggle_rapid)

def apply_script(protocol, connection, config):
    class RapidConnection(connection):
        rapid = False
        rapid_loop = None
        
        def on_login(self, name):
            self.rapid = ALWAYS_RAPID
            self.rapid_hack_detect = not self.rapid
            connection.on_login(self, name)
        
        def on_reset(self):
            if self.rapid_loop and self.rapid_loop.running:
                self.rapid_loop.stop()
            connection.on_reset(self)
        
        def on_disconnect(self):
            self.rapid = False
            if self.rapid_loop and self.rapid_loop.running:
                self.rapid_loop.stop()
            self.rapid_loop = None
            connection.on_disconnect(self)
        
        def on_block_build(self, x, y, z):
            if self.rapid:
                delay = max(0.0, RAPID_BLOCK_DELAY - self.latency / 1000.0)
                if delay > 0.0:
                    callLater(delay, resend_tool, self)
                else:
                    resend_tool(self)
            connection.on_block_build(self, x, y, z)
        
        def on_grenade_thrown(self, grenade):
            if self.rapid:
                resend_tool(self)
            connection.on_grenade_thrown(self, grenade)
        
        def on_shoot_set(self, fire):
            if self.rapid and self.rapid_loop:
                if not self.rapid_loop.running and fire:
                    self.rapid_loop.start(RAPID_INTERVAL)
                elif self.rapid_loop.running and not fire:
                    self.rapid_loop.stop()
            connection.on_shoot_set(self, fire)
    
    return protocol, RapidConnection