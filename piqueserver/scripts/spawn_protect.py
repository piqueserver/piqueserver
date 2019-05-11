"""
Protects spawned players for a specified amount of seconds.

Options
^^^^^^^

.. code-block:: guess

   [spawn_protect]
   protection_time = "3sec"

.. codeauthor:: ? & kmsi <kmsiapps@gmail.com>
"""

from pyspades.common import prettify_timespan
from piqueserver.config import config, cast_duration
from twisted.internet import reactor

spawn_protect_config = config.section("spawn_protect")
protection_time = spawn_protect_config.option("protection_time", default="3sec", cast=cast_duration)


def apply_script(protocol, connection, config):
    spawn_protect_time = protection_time.get()

    class SpawnProtectConnection(connection):
        spawn_timestamp = None

        def on_spawn(self, pos):
            self.spawn_timestamp = reactor.seconds()
            return connection.on_spawn(self, pos)

        def on_hit(self, hit_amount, hit_player, type, grenade):
            cur_timestamp = reactor.seconds() - spawn_protect_time
            if cur_timestamp < hit_player.spawn_timestamp:
                timespan = -(cur_timestamp - hit_player.spawn_timestamp)
                self.send_chat(
                    "%s is spawn-protected for %s." %
                    (hit_player.name, prettify_timespan(
                        timespan, True)))
                return False
            return connection.on_hit(
                self, hit_amount, hit_player, type, grenade)
    return protocol, SpawnProtectConnection
