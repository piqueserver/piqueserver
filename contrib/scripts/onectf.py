from pyspades.constants import *

CENTER_X = 256
CENTER_Y = 256

HIDE_X = 0
HIDE_Y = 0
HIDE_Z = 63

def apply_script(protocol, connection, config):
    game_mode = config.get('game_mode', 'ctf')
    if game_mode != 'ctf':
        return protocol, connection

    class OneCTFProtocol(protocol):
        map_changed = False
        def __init__(self, *arg, **kw):
            protocol.__init__(self, *arg, **kw)
            self.reset_flags()
        
        def reset_flags(self):
            blue_flag = self.blue_team.flag
            green_flag = self.green_team.flag
            blue_flag.player = green_flag.player = None
            z = self.map.get_z(CENTER_X, CENTER_Y)
            blue_flag.set(CENTER_X, CENTER_Y, z)
            green_flag.set(CENTER_X, CENTER_Y, z)
            blue_flag.update()
            green_flag.update()
        
        def on_game_end(self):
            self.reset_flags()
            return protocol.on_game_end(self)

    class OneCTFConnection(connection):
        def on_flag_take(self):
            flag = self.team.flag
            flag.set(HIDE_X, HIDE_Y, HIDE_Z)
            flag.update()
            # Hack until on_flag_take can be updated to return false
            # to force a flag pickup cancel
            flag.player = False
            return connection.on_flag_take(self)
        
        def on_flag_drop(self):
            flag = self.team.flag
            flag.player = None
            position = self.world_object.position
            x = int(position.x)
            y = int(position.y)
            z = int(position.z)
            z = max(0, int(position.z))
            z = self.protocol.map.get_z(x, y, z)
            flag.set(x, y, z)
            flag.update()
            return connection.on_flag_drop(self)

        def on_flag_capture(self):
            self.protocol.reset_flags()
            return connection.on_flag_capture(self)
    
    return OneCTFProtocol, OneCTFConnection