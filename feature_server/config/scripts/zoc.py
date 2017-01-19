"""
Zones of control: Dropped intel and tents exert influence
over nearby area, restricting player ability to destroy.

Maintainer: ?
"""

from twisted.internet.task import LoopingCall
from pyspades.constants import *

BK_FREE, BK_FRIENDLY, BK_ENEMY_FAR, BK_ENEMY_NEAR, BK_UNDO = range(5)

def apply_script(protocol, connection, config):

    class ZOCConnection(connection):
        block_undo = None

        def on_connect(self):
            self.block_undo = []
            self.zoc_destruction_points = 0
            return connection.on_connect(self)

        def on_spawn(self, pos):
            self.zoc_destruction_points = 0
            return connection.on_spawn(self, pos)

        def on_block_destroy(self, x, y, z, mode):
            """Restrict destruction of blocks that are on your own team and
            in a zone of control, or blocks that are on the other team and
            are too distant."""
            if not self.god:
                zoc = self.zoc_type(x, y, z)
                if zoc==BK_ENEMY_FAR:
                    self.send_chat(
                        "You're too far away to attack this area!")
                    return False
                elif zoc==BK_FRIENDLY:
                    cost = self.protocol.zoc_block_cost
                    if mode == SPADE_DESTROY:
                        cost *= 3
                    elif mode == GRENADE_DESTROY:
                        cost = self.protocol.zoc_grenade_cost
                    if self.zoc_destruction_points < cost:
                        self.send_chat("Stop destroying your territory! "+
                                       "Go fight the enemy!")
                        return False
                    else:
                        self.zoc_destruction_points -= cost
            return connection.on_block_destroy(self, x, y, z, mode)

        def own_block(self, x, y, z):
            for position in self.block_undo:
                if position[0]==x and position[1]==y and position[2]==z:
                    return True
            return False

        def on_block_build_attempt(self, x, y, z):
            zoc = self.zoc_type(x, y, z)
            if zoc == BK_ENEMY_NEAR:
                self.send_chat("You can't build in enemy territory!")
                return False
            else:
                return connection.on_block_build_attempt(self, x, y, z)

        def on_block_build(self, x, y, z):
            self.block_undo.append((x, y, z))
            if len(self.block_undo) > self.protocol.zoc_block_undo:
                del self.block_undo[0]
            return connection.on_block_build(self, x, y, z)

        def zoc_type(self, x, y, z):
            for zoc in self.protocol.zone_cache:
                if (zoc['left'] <= x and zoc['right'] >= x and
                    zoc['top'] <= y and zoc['bottom'] >= y):
                    if zoc['team'] is self.team:
                        if self.own_block(x, y, z):
                            return BK_UNDO
                        else:
                            return BK_FRIENDLY
                    else:
                        p_x, p_y, p_z = self.world_object.position.get()
                        dist_sq = (p_x - x) * (p_x - x) +\
                                  (p_y - y) * (p_y - y)
                        if self.protocol.zoc_attack_distance < dist_sq:
                            return BK_ENEMY_FAR
                        else:
                            return BK_ENEMY_NEAR
            return BK_FREE

    class ZOCProtocol(protocol):

        zone_cache = None

        zoc_radius = config.get('zoc_radius', 32)
        zoc_attack_distance = config.get('zoc_attack_distance', 64)
        zoc_attack_distance = zoc_attack_distance * zoc_attack_distance
        zoc_block_undo = config.get('zoc_block_undo', 10)

        zoc_block_cost = config.get('zoc_block_cost', 5)
        zoc_points_per_tick = config.get('zoc_points_per_tick', 1)
        zoc_point_cap = config.get('zoc_point_cap', 6 * zoc_block_cost)
        zoc_grenade_cost = config.get('zoc_grenade_cost', zoc_point_cap)

        def __init__(self, *arg, **kw):
            # we update the zones with a slow loop
            # (simpler than tracking every event that could update zones)
            protocol.__init__(self, *arg, **kw)
            self.zoc_loop = LoopingCall(self.zoc_tick)
            if not self.zoc_loop.running:
                self.zoc_loop.start(5.0)

        def _build_zoc(self, x, y, team):
            return {'team':team,
                    'left':x - self.zoc_radius,
                    'right':x + self.zoc_radius,
                    'top':y - self.zoc_radius,
                    'bottom':y + self.zoc_radius}

        def zoc_tick(self):
            self.cache_zones_of_control()
            for player in self.players.values():
                player.zoc_destruction_points += self.zoc_points_per_tick
                if player.zoc_destruction_points > self.zoc_point_cap:
                    player.zoc_destruction_points = self.zoc_point_cap

        def cache_zones_of_control(self):
            zones = []
            if self.game_mode == CTF_MODE:
                for flag in [self.green_team.flag, self.blue_team.flag]:
                    if flag.player is None:
                        zones.append(self._build_zoc(flag.x,flag.y,flag.team))
                for base in [self.green_team.base, self.blue_team.base]:
                    zones.append(self._build_zoc(base.x,base.y,base.team))
            elif self.game_mode == TC_MODE:
                for flag in self.entities:
                    zones.append(self._build_zoc(flag.x,flag.y,flag.team))
            self.zone_cache = zones

        def on_update_entity(self, entity):
            map = self.map
            desired_z = map.get_z(entity.x, entity.y)
            if int(entity.z) != int(desired_z):
                entity.z = desired_z
                return True
            return protocol.on_update_entity(self, entity)

    return ZOCProtocol, ZOCConnection
