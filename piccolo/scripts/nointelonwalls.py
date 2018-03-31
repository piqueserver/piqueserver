"""
nointelonwalls.py - prevents taking intel through walls
by kmsi(kmsiapps@gmail.com)
inspired by nospadingwalls.py & omgnograbbingthroughwallsanymore.py
Version 2(2017.12.25)
"""


def apply_script(protocol, connection, config):
    class noIntelWallsConnection(connection):

        def on_flag_take(self):
            flag = self.team.other.flag
            if not self.world_object.can_see(flag.x, flag.y, flag.z-1):
                return False
            else:
                return connection.on_flag_take(self)
    return protocol, noIntelWallsConnection
