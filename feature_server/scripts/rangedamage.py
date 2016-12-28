"""
Changes the damage values depending on distance.

Maintainer: ?
"""

from pyspades.constants import *
from math import sqrt

def point_distance2(c1, c2):
    if c1.world_object is not None and c2.world_object is not None:
        p1 = c1.world_object.position
        p2 = c2.world_object.position
        return (p1.x - p2.x)**2 + (p1.y - p2.y)**2 + (p1.z - p2.z)**2

def apply_script(protocol, connection, config):
    class RangeDamageProtocol(protocol):
        rifle_pct_per_block = config.get('rifle_pct_per_block', 0)
        shotgun_pct_per_block = config.get('shotgun_pct_per_block', 2.5)
        smg_pct_per_block = config.get('smg_pct_per_block', 1.5)
        rifle_multiplier = config.get('rifle_multiplier', 1)
        shotgun_multiplier = config.get('shotgun_multiplier', 2)
        smg_multiplier = config.get('smg_multiplier', 1.2)

    class RangeDamageConnection(connection):
        def __init__(self, *arg, **kw):
            connection.__init__(self, *arg, **kw)

        def on_hit(self, hit_amount, hit_player, type, grenade):
            result = connection.on_hit(self, hit_amount, hit_player, type,
                grenade)
            if result == False:
                return False
            if result is not None:
                hit_amount = result
            dist = sqrt(point_distance2(self, hit_player))
            if self.weapon == RIFLE_WEAPON:
                pct = (100 * self.protocol.rifle_multiplier
                       - self.protocol.rifle_pct_per_block * dist)
            elif self.weapon == SMG_WEAPON:
                pct = (100 * self.protocol.smg_multiplier
                       - self.protocol.smg_pct_per_block * dist)
            elif self.weapon == SHOTGUN_WEAPON:
                pct = (100 * self.protocol.shotgun_multiplier                
                       - self.protocol.shotgun_pct_per_block * dist)
            pct = max(0,pct)/100.0
            hit_amount = int(hit_amount * pct)
            return hit_amount
    
    return RangeDamageProtocol, RangeDamageConnection
