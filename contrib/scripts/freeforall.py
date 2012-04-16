# Free for all script written by Yourself

from random import randint

# If ALWAYS_ENABLED is False, free for all can still be enabled in the map
# metadata by setting the key 'free_for_all' to True in the extensions dictionary
ALWAYS_ENABLED = True

# If WATER_SPANS is True, then players can spawn in water
WATER_SPAWNS = False

HIDE_POS = (0, 0, 63)

def apply_script(protocol, connection, config):
    class FreeForAllProtocol(protocol):
        free_for_all = False
        old_friendly_fire = None
        def on_map_change(self, map):
            extensions = self.map_info.extensions
            if ALWAYS_ENABLED:
                self.free_for_all = True
            else:
                if extensions.has_key('free_for_all'):
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

    class FreeForAllConnection(connection):
        score_hack = False
        def on_spawn_location(self, pos):
            if not self.score_hack and self.protocol.free_for_all:
                while True:
                    x = randint(0, 511)
                    y = randint(0, 511)
                    z = self.protocol.map.get_z(x, y)
                    if z != 63 or WATER_SPAWNS:
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

        def on_kill(self, by, type, grenade):
            # Switch teams to add score hack
            if by is not None and by.team is self.team and self is not by:
                self.score_hack = True
                pos = self.world_object.position
                self.set_team(self.team.other)
                self.spawn((pos.x, pos.y, pos.z))
                self.score_hack = False
            return connection.on_kill(self, by, type, grenade)

    return FreeForAllProtocol, FreeForAllConnection