"""
Prevents taking intel through walls

Version 2(2017.12.25)

.. codeauthor:: kmsi<kmsiapps@gmail.com>
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
