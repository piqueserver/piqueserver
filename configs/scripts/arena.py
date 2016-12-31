# READ THE INSTRUCTIONS BELOW BEFORE YOU ASK QUESTIONS

# Arena game mode written by Yourself
# A game of team survival. The last team standing scores a point.

# A map that uses arena needs to be modified to have a starting area for
# each team. A starting area is enclosed and has a gate on it. Each block of a
# gate must have the EXACT same color to work properly. Between each rounds,
# the gate is rebuilt. The gates are destroyed simultaneously at the start of each
# round, releasing the players onto the map. Players are free to switch weapons
# between rounds.

# Spawn locations and gate locations MUST be present in the map metadata (map txt file)
# for arena to work properly.

# Spawn locations for the green team are set by using the data from the 'arena_green_spawn'
# tuple in the extensions dictionary. Likewise, the blue spawn is set with the 'arena_blue_spawn'
# key.

# The locations of gates is also determined in the map metadata. 'arena_gates' is a
# tuple of coordinates in the extension dictionary. Each gate needs only one block
# to be specified (since each gate is made of a uniform color)

# Sample extensions dictionary of an arena map with two gates:
# extensions = {
#     'arena': True,
#     'arena_blue_spawn' : (128, 256, 60),
#     'arena_green_spawn' : (384, 256, 60),
#     'arena_gates': ((192, 236, 59), (320, 245, 60))
# }


from pyspades.server import block_action, set_color, block_line
from pyspades import world
from pyspades.constants import *
from twisted.internet import reactor
from twisted.internet.task import LoopingCall
from commands import add, admin

# If ALWAYS_ENABLED is False, then the 'arena' key must be set to True in
# the 'extensions' dictionary in the map metadata
ALWAYS_ENABLED = True

# How long should be spent between rounds in arena (seconds)
SPAWN_ZONE_TIME = 20.0

# Maximum duration that a round can last. Time is in seconds. Set to 0 to
# disable the time limit
MAX_ROUND_TIME = 180

MAP_CHANGE_DELAY = 30.0

# Coordinates to hide the tent and the intel
HIDE_COORD = (0, 0, 63)

BUILDING_ENABLED = False

if MAX_ROUND_TIME >= 60:
    MAX_ROUND_TIME_TEXT = '%.2f minutes' % (float(MAX_ROUND_TIME)/60.0)
else:
    MAX_ROUND_TIME_TEXT = MAX_ROUND_TIME + ' seconds'

@admin
def coord(connection):
    connection.get_coord = True
    return 'Spade a block to get its coordinate.'

add(coord)

def make_color(r, g, b, a = 255):
    r = int(r)
    g = int(g)
    b = int(b)
    a = float(a)
    return b | (g << 8) | (r << 16) | (int((a / 255.0) * 128.0) << 24)

# Algorithm for minimizing the number of blocks sent for the gates using
# a block line. Probably won't find the optimal solution for shapes that are not
# rectangular prisms but it's better than nothing.
# d = changing indice
# c1 = first constant indice
# c2 = second constant indice
def partition(points, d, c1, c2):
    row = {}
    row_list = []
    for point in points:
        pc1 = point[c1]
        pc2 = point[c2]
        if not row.has_key(pc1):
            row[pc1] = {}
        dic1 = row[pc1]
        if not dic1.has_key(pc2):
            dic1[pc2] = []
            row_list.append(dic1[pc2])
        dic2 = dic1[pc2]
        dic2.append(point)
    row_list_sorted = []
    for div in row_list:
        row_list_sorted.append(sorted(div, key = lambda k: k[d]))
    # row_list_sorted is a list containing lists of points that all have the same
    # point[c1] and point[c2] values and are sorted in increasing order according to point[d]
    start_block = None
    final_blocks = []
    for block_list in row_list_sorted:
        counter = 0
        for i, block in enumerate(block_list):
            counter += 1
            if start_block is None:
                start_block = block
            if i + 1 == len(block_list):
                next_block = None
            else:
                next_block = block_list[i + 1]
            # Current AoS version seems to have an upper limit of 65 blocks for a block line
            if counter == 65 or next_block is None or block[d] + 1 != next_block[d]:
                final_blocks.append([start_block, block])
                start_block = None
                counter = 0
    return final_blocks

def minimize_block_line(points):
    x = partition(points, 0, 1, 2)
    y = partition(points, 1, 0, 2)
    z = partition(points, 2, 0, 1)
    xlen = len(x)
    ylen = len(y)
    zlen = len(z)
    if xlen <= ylen and xlen <= zlen:
        return x
    if ylen <= xlen and ylen <= zlen:
        return y
    if zlen <= xlen and zlen <= ylen:
        return z
    return x

def get_team_alive_count(team):
    count = 0
    for player in team.get_players():
        if not player.world_object.dead:
            count += 1
    return count

def get_team_dead(team):
    for player in team.get_players():
        if not player.world_object.dead:
            return False
    return True

class CustomException(Exception):
    def __init__(self, value):
        self.parameter = value

    def __str__(self):
        return repr(self.parameter)

class Gate:
    def __init__(self, x, y, z, protocol_obj):
        self.support_blocks = []
        self.blocks = []
        self.protocol_obj = protocol_obj
        map = self.protocol_obj.map
        solid, self.color = map.get_point(x, y, z)
        if not solid:
            raise CustomException('The gate coordinate (%i, %i, %i) is not solid.' % (x, y, z))
        self.record_gate(x, y, z)
        self.blocks = minimize_block_line(self.blocks)

    def build_gate(self):
        map = self.protocol_obj.map
        set_color.value = make_color(*self.color)
        set_color.player_id = block_line.player_id = 32
        self.protocol_obj.send_contained(set_color, save = True)
        for block_line_ in self.blocks:
            start_block, end_block = block_line_
            points = world.cube_line(*(start_block + end_block))
            if not points:
                continue
            for point in points:
                x, y, z = point
                if not map.get_solid(x, y, z):
                    map.set_point(x, y, z, self.color)
            block_line.x1, block_line.y1, block_line.z1 = start_block
            block_line.x2, block_line.y2, block_line.z2 = end_block
            self.protocol_obj.send_contained(block_line, save = True)

    def destroy_gate(self):
        map = self.protocol_obj.map
        block_action.player_id = 32
        block_action.value = DESTROY_BLOCK
        for block in self.support_blocks: # optimize wire traffic
            if map.get_solid(*block):
                map.remove_point(*block)
                block_action.x, block_action.y, block_action.z = block
                self.protocol_obj.send_contained(block_action, save = True)
        for block_line_ in self.blocks: # avoid desyncs
            start_block, end_block = block_line_
            points = world.cube_line(*(start_block + end_block))
            if not points:
                continue
            for point in points:
                x, y, z = point
                if map.get_solid(x, y, z):
                    map.remove_point(x, y, z)

    def record_gate(self, x, y, z):
        if x < 0 or x > 511 or y < 0 or x > 511 or z < 0 or z > 63:
            return False
        solid, color = self.protocol_obj.map.get_point(x, y, z)
        if solid:
            coordinate = (x, y, z)
            if color[0] != self.color[0] or color[1] != self.color[1] or color[2] != self.color[2]:
                return True
            for block in self.blocks:
                if coordinate == block:
                    return False
            self.blocks.append(coordinate)
            returns = (self.record_gate(x+1, y, z),
                self.record_gate(x-1, y, z),
                self.record_gate(x, y+1, z),
                self.record_gate(x, y-1, z),
                self.record_gate(x, y, z+1),
                self.record_gate(x, y, z-1))
            if True in returns:
                self.support_blocks.append(coordinate)
        return False

def apply_script(protocol, connection, config):
    class ArenaConnection(connection):
        get_coord = False

        def on_block_destroy(self, x, y, z, mode):
            returned = connection.on_block_destroy(self, x, y, z, mode)
            if self.get_coord:
                self.get_coord = False
                self.send_chat('Coordinate: %i, %i, %i' % (x, y, z))
                return False
            return returned

        def on_disconnect(self):
            if self.protocol.arena_running:
                if self.world_object is not None:
                    self.world_object.dead = True
                    self.protocol.check_round_end()
            return connection.on_disconnect(self)

        def on_kill(self, killer, type, grenade):
            if self.protocol.arena_running and type != TEAM_CHANGE_KILL:
                if self.world_object is not None:
                    self.world_object.dead = True
                    self.protocol.check_round_end(killer)
            return connection.on_kill(self, killer, type, grenade)

        def on_team_join(self, team):
            returned = connection.on_team_join(self, team)
            if returned is False:
                return False
            if self.protocol.arena_running:
                if self.world_object is not None and not self.world_object.dead:
                    self.world_object.dead = True
                    self.protocol.check_round_end()
            return returned

        def get_respawn_time(self):
            if self.protocol.arena_running:
                return -1
            else:
                return 1

        def respawn(self):
            if self.protocol.arena_running:
                return False
            return connection.respawn(self)

        def on_spawn(self, pos):
            returned = connection.on_spawn(self, pos)
            if self.protocol.arena_running:
                self.kill()
            return returned

        def on_spawn_location(self, pos):
            if self.protocol.arena_enabled:
                return self.team.arena_spawn
            return connection.on_spawn_location(self, pos)

        def on_flag_take(self):
            if self.protocol.arena_take_flag:
                self.protocol.arena_take_flag = False
                return connection.on_flag_take(self)
            return False

        def on_refill(self):
            returned = connection.on_refill(self)
            if self.protocol.arena_running:
                return False
            return returned

    class ArenaProtocol(protocol):
        old_respawn_time = None
        old_building = None
        old_killing = None
        arena_enabled = False
        arena_running = False
        arena_counting_down = False
        arena_take_flag = False
        arena_countdown_timers = None
        arena_limit_timer = None

        def check_round_end(self, killer = None, message = True):
            if not self.arena_running:
                return
            for team in (self.green_team, self.blue_team):
                if get_team_dead(team):
                    self.arena_win(team.other, killer)
                    return
            if message:
                self.arena_remaining_message()

        def arena_time_limit(self):
            self.arena_limit_timer = None
            green_team = self.green_team
            blue_team = self.blue_team
            green_count = get_team_alive_count(green_team)
            blue_count = get_team_alive_count(blue_team)
            if green_count > blue_count:
                self.arena_win(green_team)
            elif green_count < blue_count:
                self.arena_win(blue_team)
            else:
                self.send_chat('Round ends in a tie.')
            self.begin_arena_countdown()

        def arena_win(self, team, killer = None):
            if not self.arena_running:
                return
            if killer is None or killer.team is not team:
                for player in team.get_players():
                    killer = player
                    break
            if killer is not None:
                self.arena_take_flag = True
                killer.take_flag()
                killer.capture_flag()
            self.send_chat(team.name + ' team wins the round!')
            self.begin_arena_countdown()

        def arena_remaining_message(self):
            if not self.arena_running:
                return
            green_team = self.green_team
            blue_team = self.blue_team
            for team in (self.green_team, self.blue_team):
                num = get_team_alive_count(team)
                team.arena_message = '%i player' % num
                if num != 1:
                    team.arena_message += 's'
                team.arena_message += ' on ' + team.name
            self.send_chat('%s and %s remain.' % (green_team.arena_message, blue_team.arena_message))

        def on_map_change(self, map):
            extensions = self.map_info.extensions
            if ALWAYS_ENABLED:
                self.arena_enabled = True
            else:
                if extensions.has_key('arena'):
                    self.arena_enabled = extensions['arena']
                else:
                    self.arena_enabled = False
            if self.arena_enabled:
                self.old_respawn_time = self.respawn_time
                self.respawn_time = 0
                self.old_building = self.building
                self.old_killing = self.killing
                self.gates = []
                if extensions.has_key('arena_gates'):
                    for gate in extensions['arena_gates']:
                        self.gates.append(Gate(*gate, protocol_obj=self))
                if extensions.has_key('arena_green_spawn'):
                    self.green_team.arena_spawn = extensions['arena_green_spawn']
                else:
                    raise CustomException('No arena_green_spawn given in map metadata.')
                if extensions.has_key('arena_blue_spawn'):
                    self.blue_team.arena_spawn = extensions['arena_blue_spawn']
                else:
                    raise CustomException('No arena_blue_spawn given in map metadata.')
                self.delay_arena_countdown(MAP_CHANGE_DELAY)
                self.begin_arena_countdown()
            else:
                # Cleanup after a map change
                if self.old_respawn_time is not None:
                    self.respawn_time = self.old_respawn_time
                if self.old_building is not None:
                    self.building = self.old_building
                if self.old_killing is not None:
                    self.killing = self.old_killing
                self.arena_enabled = False
                self.arena_running = False
                self.arena_counting_down = False
                self.arena_limit_timer = None
                self.old_respawn_time = None
                self.old_building = None
                self.old_killing = None
            return protocol.on_map_change(self, map)

        def build_gates(self):
            for gate in self.gates:
                gate.build_gate()

        def destroy_gates(self):
            for gate in self.gates:
                gate.destroy_gate()

        def arena_spawn(self):
            for player in self.players.values():
                if player.team.spectator:
                    continue
                if player.world_object.dead:
                    player.spawn(player.team.arena_spawn)
                else:
                    player.set_location(player.team.arena_spawn)
                    player.refill()

        def begin_arena_countdown(self):
            if self.arena_limit_timer is not None:
                if self.arena_limit_timer.cancelled == 0 and self.arena_limit_timer.called == 0:
                    self.arena_limit_timer.cancel()
                    self.arena_limit_timer = None
            if self.arena_counting_down:
                return
            self.arena_running = False
            self.arena_limit_timer = None
            self.arena_counting_down = True
            self.killing = False
            self.building = False
            self.build_gates()
            self.arena_spawn()
            self.send_chat('The round will begin in %i seconds.' % SPAWN_ZONE_TIME)
            self.arena_countdown_timers = [reactor.callLater(SPAWN_ZONE_TIME, self.begin_arena)]
            for time in xrange(1, 6):
                self.arena_countdown_timers.append(reactor.callLater(SPAWN_ZONE_TIME - time, self.send_chat, str(time)))

        def delay_arena_countdown(self, amount):
            if self.arena_counting_down:
                for timer in self.arena_countdown_timers:
                    if timer.cancelled == 0 and timer.called == 0:
                        timer.delay(amount)

        def begin_arena(self):
            self.arena_counting_down = False
            for team in (self.green_team, self.blue_team):
                if team.count() == 0:
                    self.send_chat('Not enough players on the %s team to begin.' % team.name)
                    self.begin_arena_countdown()
                    return
            self.arena_running = True
            self.killing = True
            self.building = BUILDING_ENABLED
            self.destroy_gates()
            self.send_chat('Go!')
            if MAX_ROUND_TIME > 0:
                self.send_chat('There is a time limit of %s for this round.' % MAX_ROUND_TIME_TEXT)
                self.arena_limit_timer = reactor.callLater(MAX_ROUND_TIME, self.arena_time_limit)

        def on_base_spawn(self, x, y, z, base, entity_id):
            if not self.arena_enabled:
                return protocol.on_base_spawn(self, x, y, z, base, entity_id)
            return HIDE_COORD

        def on_flag_spawn(self, x, y, z, flag, entity_id):
            if not self.arena_enabled:
                return protocol.on_base_spawn(self, x, y, z, flag, entity_id)
            return HIDE_COORD

    return ArenaProtocol, ArenaConnection
