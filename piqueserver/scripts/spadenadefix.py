"""
spadenadefix.py - blocks spade-nade bug
by kmsi(kmsiapps@gmail.com)
version 2(2017.12.23)
"""

from pyspades.constants import SPADE_TOOL

def apply_script(protocol, connection, config):
    class SpadenadeConnection(connection):
        def on_secondary_fire_set(self, secondary):
            self.wasSpade = (self.tool == SPADE_TOOL)
        
        def on_grenade(self, time_left):
            print(self.wasSpade)
            if(self.world_object.secondary_fire and self.wasSpade):
                self.send_chat('Spade-Grenade bug is blocked.')
                self.wasSpade = False
                return False
            else:
                self.wasSpade = False
                return connection.on_grenade(self, time_left)

    return protocol, SpadenadeConnection
