"""
Changes the damage values depending on distance.

Options
^^^^^^^

.. code-block:: guess

   [rangedamange.rifle]
   pct_per_block = 0 # percentage per block?
   multiplier = 1

   [rangedamange.smg]
   pct_per_block = 0
   multiplier = 1

   [rangedamange.shotgun]
   pct_per_block = 0
   multiplier = 1

.. codeauthor:: ?
"""

from pyspades.constants import (SHOTGUN_WEAPON, SMG_WEAPON, RIFLE_WEAPON)
from pyspades.collision import distance_3d_vector
from math import sqrt
from piqueserver.config import config

range_damage_config = config.section("rangedamange")
rifle_config = range_damage_config.section("rifle")
smg_config = range_damage_config.section("smg")
shotgun_config = range_damage_config.section("shotgun")

rifle_pct_per_block = rifle_config.option("pct_per_block", 0)
rifle_multiplier = rifle_config.option("multiplier", 1)

shotgun_pct_per_block = shotgun_config.option("pct_per_block", 2.5)
shotgun_multiplier = shotgun_config.option("multiplier", 2)

smg_pct_per_block = smg_config.option("pct_per_block", 1.5)
smg_multiplier = smg_config.option("multiplier", 1.2)


def apply_script(protocol, connection, config):

    class RangeDamageConnection(connection):

        def __init__(self, *arg, **kw):
            connection.__init__(self, *arg, **kw)

        def on_hit(self, hit_amount, hit_player, type, grenade):
            result = connection.on_hit(self, hit_amount, hit_player, type,
                                       grenade)
            if result == False:
                return False
            if grenade:  # Don't reduce damage when using grenade e.g. airstrike
                return connection.on_hit(self, hit_amount, hit_player, type, grenade)
            if self.world_object and hit_player.world_object:
                if result is not None:
                    hit_amount = result
                dist = distance_3d_vector(
                    self.world_object.position, hit_player.world_object.position)
                if self.weapon == RIFLE_WEAPON:
                    pct = (100 * rifle_multiplier.get()
                           - rifle_pct_per_block.get() * dist)
                elif self.weapon == SMG_WEAPON:
                    pct = (100 * smg_multiplier.get()
                           - smg_pct_per_block.get() * dist)
                elif self.weapon == SHOTGUN_WEAPON:
                    pct = (100 * shotgun_multiplier.get()
                           - shotgun_pct_per_block.get() * dist)
                pct = max(0, pct) / 100.0
                hit_amount = int(hit_amount * pct)
                return hit_amount

    return protocol, RangeDamageConnection
