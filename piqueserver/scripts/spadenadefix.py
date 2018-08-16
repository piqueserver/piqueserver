"""
Prevents spade-nade bug

version 2(2017.12.23)

.. codeauthor:: kmsi<kmsiapps@gmail.com>
"""

from pyspades.constants import SPADE_TOOL

def apply_script(protocol, connection, config):
    class SpadenadeConnection(connection):
        def on_secondary_fire_set(self, secondary):
            self.was_spade = (self.tool == SPADE_TOOL)

        def on_grenade(self, time_left):
            if(self.world_object.secondary_fire and self.was_spade):
                self.send_chat('Spade-Grenade bug is blocked.')
                self.was_spade = False
                return False
            else:
                self.was_spade = False
                return connection.on_grenade(self, time_left)

    return protocol, SpadenadeConnection
