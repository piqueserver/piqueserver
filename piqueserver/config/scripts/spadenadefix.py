"""
spadenadefix.py - blocks spade-nade bug
by kmsi(kmsiapps@gmail.com)
version 1(2017.01.21)
"""


def apply_script(protocol, connection, config):
    class SpadenadeConnection(connection):

        def on_grenade(self, time_left):
            if(self.world_object.secondary_fire):
                self.send_chat('Spade-Grenade bug is blocked.')
                return False
            else:
                return connection.on_grenade(self, time_left)
    return protocol, SpadenadeConnection
