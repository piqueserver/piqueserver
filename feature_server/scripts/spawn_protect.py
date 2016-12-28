"""
Protects spawned players for a specified amount of seconds.

Maintainer: ?
"""

from pyspades.common import prettify_timespan
from twisted.internet import reactor

def apply_script(protocol, connection, config):
    spawn_protect_time = config.get('spawn_protect_time', 3.0)
    
    class SpawnProtectConnection(connection):
        spawn_timestamp = None

        def on_spawn(self, pos):
            self.spawn_timestamp = reactor.seconds()
            return connection.on_spawn(self, pos)

        def on_hit(self, hit_amount, player, type, grenade):
            cur_timestamp = reactor.seconds() - spawn_protect_time
            if cur_timestamp < hit_player.spawn_timestamp:
                timespan = -(cur_timestamp - hit_player.spawn_timestamp)
                self.send_chat(
                "%s is spawn-protected for %s." %
                    (player.name,
                     prettify_timespan(timespan, True)))
                return False
            return connection.on_hit(self, hit_amount, player, type, grenade)
    
    return protocol, SpawnProtectConnection
