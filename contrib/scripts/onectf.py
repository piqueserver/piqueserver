from pyspades.constants import *
from commands import add, admin
from pyspades.collision import vector_collision

CENTER_X = 256
CENTER_Y = 256

HIDE_X = 0
HIDE_Y = 0
HIDE_Z = 63

# In reverse ctf, the goal is to take the intel to the enemy base
REVERSE_CTF = False
# The message to send when a player takes the intel to the wrong base
# when playing reverse ctf
REVERSE_CTF_MESSAGE_ENABLED = True
REVERSE_CTF_MESSAGE = 'Take the intel to the enemy base to score.'

@admin
def resetflags(connection):
    connection.protocol.reset_flags()

add(resetflags)

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
        
        def on_map_change(self, m):
            self.map_changed = True
            return protocol.on_map_change(self, m)

    class OneCTFConnection(connection):
        def on_flag_take(self):
            flag = self.team.flag
            if flag.player is None:
                flag.set(HIDE_X, HIDE_Y, HIDE_Z)
                flag.update()
                if REVERSE_CTF and REVERSE_CTF_MESSAGE_ENABLED:
                    self.send_chat(REVERSE_CTF_MESSAGE)
            else:
                return False
            return connection.on_flag_take(self)
        
        def on_flag_drop(self):
            flag = self.team.flag
            position = self.world_object.position
            x = int(position.x)
            y = int(position.y)
            z = int(position.z)
            z = max(0, int(position.z))
            z = self.protocol.map.get_z(x, y, z)
            flag.set(x, y, z)
            flag.update()
            return connection.on_flag_drop(self)
        
        def on_position_update(self):
            if REVERSE_CTF:
                if vector_collision(self.world_object.position, self.team.other.base):
                    other_flag = self.team.other.flag
                    if other_flag.player is self:
                        connection.capture_flag(self)
            return connection.on_position_update(self)

        def capture_flag(self):
            if REVERSE_CTF:
                if REVERSE_CTF_MESSAGE_ENABLED:
                    self.send_chat(REVERSE_CTF_MESSAGE)
                return False
            return connection.capture_flag(self)

        def on_flag_capture(self):
            self.protocol.reset_flags()
            return connection.on_flag_capture(self)
        
        def on_spawn(self, pos):
            if self.protocol.map_changed == True:
                self.protocol.map_changed = False
                self.protocol.reset_flags()
            return connection.on_spawn(self, pos)
    
    return OneCTFProtocol, OneCTFConnection