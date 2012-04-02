from pyspades.constants import *
from commands import add, admin
from pyspades.collision import vector_collision

FLAG_SPAWN_POS = (256, 256)

HIDE_POS = (0, 0, 63)

# 1CTF and R1CTF can be enabled via the map metadata. Enable it by setting
# 'one_ctf' to 'True' or 'reverse_one_ctf' to 'True' in the extensions dictionary. ex:
# extensions = {'reverse_one_ctf': True}

DISABLED, ONE_CTF, REVERSE_ONE_CTF = xrange(3)

ONE_CTF_MODE = REVERSE_ONE_CTF

# In reverse ctf, the goal is to take the intel to the enemy base

# The message to send when a player takes the intel to the wrong base
# when playing reverse ctf
REVERSE_ONE_CTF_MESSAGE = 'Take the intel to the enemy base to score.'

def apply_script(protocol, connection, config):
    game_mode = config.get('game_mode', 'ctf')
    if game_mode != 'ctf':
        return protocol, connection

    class OneCTFProtocol(protocol):
        one_ctf = False
        reverse_one_ctf = False

        def onectf_reset_flag(self, flag):
            z = self.map.get_z(*self.one_ctf_spawn_pos)
            pos = (self.one_ctf_spawn_pos[0], self.one_ctf_spawn_pos[1], z)
            if flag is not None:
                flag.player = None
                flag.set(*pos)
                flag.update()
            return pos

        def onectf_reset_flags(self):
            if self.one_ctf or self.reverse_one_ctf:
                self.onectf_reset_flag(self.blue_team.flag)
                self.onectf_reset_flag(self.green_team.flag)
        
        def on_game_end(self):
            if self.one_ctf or self.reverse_one_ctf:
                self.onectf_reset_flags()
            return protocol.on_game_end(self)

        def on_map_change(self, map):
            self.one_ctf = self.reverse_one_ctf = False
            self.one_ctf_spawn_pos = FLAG_SPAWN_POS
            extensions = self.map_info.extensions
            if ONE_CTF_MODE == ONE_CTF:
                self.one_ctf = True
            elif ONE_CTF_MODE == REVERSE_ONE_CTF:
                self.reverse_one_ctf = True
            elif extensions.has_key('one_ctf'):
                self.one_ctf = extensions['one_ctf']
            if not self.one_ctf and extensions.has_key('reverse_one_ctf'):
                self.reverse_one_ctf = extensions['reverse_one_ctf']
            if extensions.has_key('one_ctf_spawn_pos'):
                self.one_ctf_spawn_pos = extensions['one_ctf_spawn_pos']
            return protocol.on_map_change(self, map)

        def on_flag_spawn(self, x, y, z, flag, entity_id):
            pos = self.onectf_reset_flag(flag.team.other.flag)
            protocol.on_flag_spawn(self, pos[0], pos[1], pos[2], flag, entity_id)
            return pos

    class OneCTFConnection(connection):
        def on_flag_take(self):
            if self.protocol.one_ctf or self.protocol.reverse_one_ctf:
                flag = self.team.flag
                if flag.player is None:
                    flag.set(*HIDE_POS)
                    flag.update()
                    if self.protocol.reverse_one_ctf:
                        self.send_chat(REVERSE_ONE_CTF_MESSAGE)
                else:
                    return False
            return connection.on_flag_take(self)
        
        def on_flag_drop(self):
            if self.protocol.one_ctf or self.protocol.reverse_one_ctf:
                flag = self.team.flag
                position = self.world_object.position
                x, y, z = int(position.x), int(position.y), max(0, int(position.z))
                z = self.protocol.map.get_z(x, y, z)
                flag.set(x, y, z)
                flag.update()
            return connection.on_flag_drop(self)
        
        def on_position_update(self):
            if self.protocol.reverse_one_ctf:
                if vector_collision(self.world_object.position, self.team.other.base):
                    other_flag = self.team.other.flag
                    if other_flag.player is self:
                        connection.capture_flag(self)
            return connection.on_position_update(self)

        def capture_flag(self):
            if self.protocol.reverse_one_ctf:
                self.send_chat(REVERSE_ONE_CTF_MESSAGE)
                return False
            return connection.capture_flag(self)

        def on_flag_capture(self):
            if self.protocol.one_ctf or self.protocol.reverse_one_ctf:
                self.protocol.onectf_reset_flags()
            return connection.on_flag_capture(self)
    
    return OneCTFProtocol, OneCTFConnection