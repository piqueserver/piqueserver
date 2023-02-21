"""
Free for All: shoot anyone

Options
^^^^^^^
.. code-block:: toml
    [freeforall]
    # If ALWAYS_ENABLED is False, free for all can still be enabled in the map
    # metadata by setting the key 'free_for_all' to True in the extensions
    # dictionary
    always_enabled = true

    # If WATER_SPAWNS is True, then players can spawn in water
    water_spawns = false

    # If ISOLATE_PLAYER is True, then player will be alone in
    # the blue team, vs all greens. This auto disable use_score_hack
    isolate_player = true

    # If USE_SCORE_HACK is True, then when you kill someone
    # that player will appear to be on the other team, so you can
    # get score when playing on voxlap
    use_score_hack = false
..
"""
# Free for all script written by Yourself

from random import randint

from pyspades.contained import CreatePlayer, ExistingPlayer
from piqueserver.config import config
from pyspades.constants import CTF_MODE

FFA_CONFIG = config.section("freeforall")
ALWAYS_ENABLED = FFA_CONFIG.option("always_enabled", default=True)
WATER_SPAWNS = FFA_CONFIG.option("water_spawns", default=False)
ISOLATE_PLAYER = FFA_CONFIG.option("isolate_player", default=True)
USE_SCORE_HACK = FFA_CONFIG.option("use_score_hack", default=False)

HIDE_POS = (0, 0, 63)


def apply_script(protocol, connection, config):
    class FreeForAllProtocol(protocol):
        game_mode = CTF_MODE
        free_for_all = False
        old_friendly_fire = None

        def on_map_change(self, map):
            extensions = self.map_info.extensions
            if ALWAYS_ENABLED.get():
                self.free_for_all = True
            else:
                if 'free_for_all' in extensions:
                    self.free_for_all = extensions['free_for_all']
                else:
                    self.free_for_all = False
            if self.free_for_all:
                self.old_friendly_fire = self.friendly_fire
                self.friendly_fire = True
            else:
                if self.old_friendly_fire is not None:
                    self.friendly_fire = self.old_friendly_fire
                    self.old_friendly_fire = None
            return protocol.on_map_change(self, map)

        def on_base_spawn(self, x, y, z, base, entity_id):
            if self.free_for_all:
                return HIDE_POS
            return protocol.on_base_spawn(self, x, y, z, base, entity_id)

        def on_flag_spawn(self, x, y, z, flag, entity_id):
            if self.free_for_all:
                return HIDE_POS
            return protocol.on_flag_spawn(self, x, y, z, flag, entity_id)

        def broadcast_contained(self, contained, unsequenced=False,
                                sender=None, team=None, save=False, rule=None):
            if ISOLATE_PLAYER.get():
                if contained.id == CreatePlayer.id:
                    if contained.team != -1:
                        player = self.players[contained.player_id]
                        contained.team = self.team_1.id

                        player.send_contained(contained)
                        contained.team = self.team_2.id
                        sender = player

            return protocol.broadcast_contained(self, contained, unsequenced,
                                                sender, team, save, rule)

    class FreeForAllConnection(connection):
        score_hack = False

        def on_team_join(self, team):
            if team.spectator or not ISOLATE_PLAYER.get():
                return team

            return self.protocol.team_2

        def on_spawn_location(self, pos):
            if not self.score_hack and self.protocol.free_for_all:
                while True:
                    x = randint(0, 511)
                    y = randint(0, 511)
                    z = self.protocol.map.get_z(x, y)
                    if z != 63 or WATER_SPAWNS.get():
                        break
                # Magic numbers taken from server.py spawn function
                z -= 2.4
                x += 0.5
                y += 0.5
                return (x, y, z)
            return connection.on_spawn_location(self, pos)

        def on_refill(self):
            if self.protocol.free_for_all:
                return False
            return connection.on_refill(self)

        def on_flag_take(self):
            if self.protocol.free_for_all:
                return False
            return connection.on_flag_take(self)

        def on_kill(self, by, _type, grenade):
            # Switch teams to add score hack
            if USE_SCORE_HACK.get() and not ISOLATE_PLAYER.get():
                if by is not None and by.team is self.team and self is not by:
                    self.score_hack = True
                    pos = self.world_object.position
                    self.set_team(self.team.other)
                    self.spawn((pos.x, pos.y, pos.z))
                    self.score_hack = False

            return connection.on_kill(self, by, _type, grenade)

    return FreeForAllProtocol, FreeForAllConnection
