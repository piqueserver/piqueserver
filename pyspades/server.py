# Copyright (c) Mathias Kaerlev 2011-2012.

# This file is part of pyspades.

# pyspades is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

# pyspades is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with pyspades.  If not, see <http://www.gnu.org/licenses/>.

from twisted.internet import reactor
from twisted.internet.task import LoopingCall
from pyspades.protocol import BaseConnection, BaseProtocol
from pyspades.bytes import ByteReader, ByteWriter
from pyspades.packet import load_client_packet
from pyspades.common import *
from pyspades.constants import *
from pyspades import contained as loaders
from pyspades.types import MultikeyDict, IDPool
from pyspades.master import get_master_connection
from pyspades.collision import vector_collision, collision_3d
from pyspades import world
from pyspades.debug import *
from pyspades.weapon import WEAPONS
import enet

import random
import math
import shlex
import textwrap
import collections
import zlib

COMPRESSION_LEVEL = 9

create_player = loaders.CreatePlayer()
position_data = loaders.PositionData()
orientation_data = loaders.OrientationData()
input_data = loaders.InputData()
grenade_packet = loaders.GrenadePacket()
set_tool = loaders.SetTool()
set_color = loaders.SetColor()
fog_color = loaders.FogColor()
existing_player = loaders.ExistingPlayer()
player_left = loaders.PlayerLeft()
block_action = loaders.BlockAction()
kill_action = loaders.KillAction()
chat_message = loaders.ChatMessage()
map_data = loaders.MapChunk()
map_start = loaders.MapStart()
state_data = loaders.StateData()
ctf_data = loaders.CTFState()
tc_data = loaders.TCState()
intel_drop = loaders.IntelDrop()
intel_pickup = loaders.IntelPickup()
intel_capture = loaders.IntelCapture()
restock = loaders.Restock()
move_object = loaders.MoveObject()
set_hp = loaders.SetHP()
change_weapon = loaders.ChangeWeapon()
change_team = loaders.ChangeTeam()
weapon_reload = loaders.WeaponReload()
territory_capture = loaders.TerritoryCapture()
progress_bar = loaders.ProgressBar()
world_update = loaders.WorldUpdate()
block_line = loaders.BlockLine()
weapon_input = loaders.WeaponInput()

def check_nan(*values):
    for value in values:
        if math.isnan(value):
            return True
    return False

def parse_command(input):
    value = encode(input)
    try:
        splitted = shlex.split(value)
    except ValueError:
        # shlex failed. let's just split per space
        splitted = value.split(' ')
    if splitted:
        command = splitted.pop(0)
    else:
        command = ''
    splitted = [decode(value) for value in splitted]
    return decode(command), splitted

class SlidingWindow(object):
    def __init__(self, entries):
        self.entries = entries
        self.window = collections.deque()

    def add(self, value):
        self.window.append(value)
        if len(self.window) <= self.entries:
            return
        self.window.popleft()

    def check(self):
        return len(self.window) == self.entries

    def get(self):
        return self.window[0], self.window[-1]

class MapGeneratorChild(object):
    pos = 0
    def __init__(self, generator):
        self.parent = generator

    def get_size(self):
        return self.parent.get_size()

    def read(self, size):
        pos = self.pos
        if pos + size > self.parent.pos:
            self.parent.read(size)
        data = self.parent.all_data[pos:pos+size]
        self.pos += len(data)
        return data

    def data_left(self):
        return self.parent.data_left() or self.pos < self.parent.pos

class ProgressiveMapGenerator(object):
    data = ''
    done = False

    # parent attributes
    all_data = ''
    pos = 0
    def __init__(self, map, parent = False):
        self.parent = parent
        self.generator = map.get_generator()
        self.compressor = zlib.compressobj(COMPRESSION_LEVEL)

    def get_size(self):
        return 1.5 * 1024 * 1024 # 2 mb

    def read(self, size):
        data = self.data
        generator = self.generator
        if len(data) < size and generator is not None:
            while 1:
                map_data = generator.get_data(1024)
                if generator.done:
                    self.generator = None
                    data += self.compressor.flush()
                    break
                data += self.compressor.compress(map_data)
                if len(data) >= size:
                    break
        if self.parent:
            # save the data in case we are a parent
            self.all_data += data
            self.pos += len(data)
        else:
            self.data = data[size:]
            return data[:size]

    def get_child(self):
        return MapGeneratorChild(self)

    def data_left(self):
        return bool(self.data) or self.generator is not None

class ServerConnection(BaseConnection):
    address = None
    player_id = None
    map_packets_sent = 0
    team = None
    weapon = None
    weapon_object = None
    name = None
    kills = 0
    hp = None
    tool = None
    color = (0x70, 0x70, 0x70)
    grenades = None
    blocks = None
    spawn_call = None
    respawn_time = None
    saved_loaders = None
    last_refill = None
    last_block_destroy = None
    filter_visibility_data = False
    filter_animation_data = False
    freeze_animation = False
    filter_weapon_input = False
    speedhack_detect = False
    rapid_hack_detect = False
    timers = None
    world_object = None
    last_block = None
    map_data = None
    last_position_update = None

    def __init__(self, *arg, **kw):
        BaseConnection.__init__(self, *arg, **kw)
        protocol = self.protocol
        address = self.peer.address
        self.address = (address.host, address.port)
        self.respawn_time = protocol.respawn_time
        self.rapids = SlidingWindow(RAPID_WINDOW_ENTRIES)

    def on_connect(self):
        if self.peer.eventData != self.protocol.version:
            self.disconnect(ERROR_WRONG_VERSION)
            return
        max_players = min(32, self.protocol.max_players)
        if len(self.protocol.connections) > max_players:
            self.disconnect(ERROR_FULL)
            return
        if self.protocol.max_connections_per_ip:
            shared = [conn for conn in
                self.protocol.connections.values()
                if conn.address[0] == self.address[0]]
            if len(shared) > self.protocol.max_connections_per_ip:
                self.disconnect(ERROR_KICKED)
                return
        if not self.disconnected:
            self._connection_ack()

    def loader_received(self, loader):
        if self.player_id is not None:
            contained = load_client_packet(ByteReader(loader.data))
            if contained.id in (loaders.ExistingPlayer.id,
                                loaders.ShortPlayerData.id):
                old_team = self.team
                team = self.protocol.teams[contained.team]
                if self.on_team_join(team) == False:
                    if not team.spectator:
                        team = team.other
                self.team = team
                if self.name is None:
                    name = contained.name
                     # vanilla AoS behaviour
                    if name == 'Deuce':
                        name = name + str(self.player_id)
                    self.name = self.protocol.get_name(name)
                    self.protocol.players[self.name, self.player_id] = self
                    self.on_login(self.name)
                else:
                    self.on_team_changed(old_team)
                self.set_weapon(contained.weapon, True)
                if self.protocol.speedhack_detect:
                    self.speedhack_detect = True
                self.rapid_hack_detect = True
                if team.spectator:
                    if self.world_object is not None:
                        self.world_object.delete()
                        self.world_object = None
                self.spawn()
                return
            if self.hp:
                world_object = self.world_object
                if contained.id == loaders.OrientationData.id:
                    x, y, z = contained.x, contained.y, contained.z
                    if check_nan(x, y, z):
                        self.on_hack_attempt(
                            'Invalid orientation data received')
                        return
                    returned = self.on_orientation_update(x, y, z)
                    if returned == False:
                        return
                    if returned is not None:
                        x, y, z = returned
                    world_object.set_orientation(x, y, z)
                elif contained.id == loaders.PositionData.id:
                    current_time = reactor.seconds()
                    last_update = self.last_position_update
                    self.last_position_update = current_time
                    if last_update is not None:
                        dt = current_time - last_update
                        if dt < MAX_POSITION_RATE:
                            self.set_location()
                            return
                    x, y, z = contained.x, contained.y, contained.z
                    if check_nan(x, y, z):
                        self.on_hack_attempt(
                            'Invalid position data received')
                        return
                    position = world_object.position
                    if not self.is_valid_position(x, y, z):
                        # vanilla behaviour
                        self.set_location()
                        return
                    if not self.freeze_animation:
                        world_object.set_position(x, y, z)
                        self.on_position_update()
                    if self.filter_visibility_data:
                        return
                    game_mode = self.protocol.game_mode
                    if game_mode == CTF_MODE:
                        other_flag = self.team.other.flag
                        if vector_collision(world_object.position,
                        self.team.base):
                            if other_flag.player is self:
                                self.capture_flag()
                            self.check_refill()
                        if other_flag.player is None and vector_collision(
                        world_object.position, other_flag):
                            self.take_flag()
                    elif game_mode == TC_MODE:
                        for entity in self.protocol.entities:
                            collides = vector_collision(entity,
                                world_object.position, TC_CAPTURE_DISTANCE)
                            if self in entity.players:
                                if not collides:
                                    entity.remove_player(self)
                            else:
                                if collides:
                                    entity.add_player(self)
                            if collides and vector_collision(entity,
                            world_object.position):
                                self.check_refill()
                elif contained.id == loaders.WeaponInput.id:
                    primary = contained.primary
                    secondary = contained.secondary
                    if world_object.primary_fire != primary:
                        if self.tool == WEAPON_TOOL:
                            self.weapon_object.set_shoot(primary)
                        if self.tool == WEAPON_TOOL or self.tool == SPADE_TOOL:
                            self.on_shoot_set(primary)
                    if world_object.secondary_fire != secondary:
                        self.on_secondary_fire_set(secondary)
                    world_object.primary_fire = primary
                    world_object.secondary_fire = secondary
                    if self.filter_weapon_input:
                        return
                    contained.player_id = self.player_id
                    self.protocol.send_contained(contained, sender = self)
                elif contained.id == loaders.InputData.id:
                    returned = self.on_walk_update(contained.up, contained.down,
                        contained.left, contained.right)
                    if returned is not None:
                        up, down, left, right = returned
                        if (up != contained.up or down != contained.down or
                            left != contained.left or right != contained.right):
                            (contained.up, contained.down, contained.left,
                                contained.right) = returned
                            ## XXX unsupported
                            #~ self.send_contained(contained)
                    if not self.freeze_animation:
                        world_object.set_walk(contained.up, contained.down,
                            contained.left, contained.right)
                    contained.player_id = self.player_id
                    z_vel = world_object.velocity.z
                    if contained.jump and not (z_vel >= 0 and z_vel < 0.017):
                        contained.jump = False
                    ## XXX unsupported for now
                    # returned = self.on_animation_update(contained.primary_fire,
                        # contained.secondary_fire, contained.jump,
                        # contained.crouch)
                    # if returned is not None:
                        # fire1, fire2, jump, crouch = returned
                        # if (fire1 != contained.primary_fire or
                            # fire2 != contained.secondary_fire or
                            # jump != contained.jump or
                            # crouch != contained.crouch):
                            # (contained.primary_fire, contained.secondary_fire,
                                # contained.jump, contained.crouch) = returned
                            # self.send_contained(contained)
                    returned = self.on_animation_update(contained.jump,
                        contained.crouch, contained.sneak, contained.sprint)
                    if returned is not None:
                        jump, crouch, sneak, sprint = returned
                        if (jump != contained.jump or crouch != contained.crouch or
                            sneak != contained.sneak or sprint != contained.sprint):
                            (contained.jump, contained.crouch, contained.sneak,
                                contained.sprint) = returned
                            self.send_contained(contained)
                    if not self.freeze_animation:
                        world_object.set_animation(contained.jump,
                            contained.crouch, contained.sneak, contained.sprint)
                    if self.filter_visibility_data or self.filter_animation_data:
                        return
                    self.protocol.send_contained(contained, sender = self)
                elif contained.id == loaders.WeaponReload.id:
                    self.weapon_object.reload()
                    if self.filter_animation_data:
                        return
                    contained.player_id = self.player_id
                    self.protocol.send_contained(contained, sender = self)
                elif contained.id == loaders.HitPacket.id:
                    value = contained.value
                    is_melee = value == MELEE
                    if not is_melee and self.weapon_object.is_empty():
                        return
                    try:
                        player = self.protocol.players[contained.player_id]
                    except KeyError:
                        return
                    valid_hit = world_object.validate_hit(player.world_object,
                        value, HIT_TOLERANCE)
                    if not valid_hit:
                        return
                    position1 = world_object.position
                    position2 = player.world_object.position
                    if is_melee:
                        if not vector_collision(position1, position2,
                                                MELEE_DISTANCE):
                            return
                        hit_amount = self.protocol.melee_damage
                    else:
                        hit_amount = self.weapon_object.get_damage(
                            value, position1, position2)
                    if is_melee:
                        type = MELEE_KILL
                    elif contained.value == HEAD:
                        type = HEADSHOT_KILL
                    else:
                        type = WEAPON_KILL
                    returned = self.on_hit(hit_amount, player, type, None)
                    if returned == False:
                        return
                    elif returned is not None:
                        hit_amount = returned
                    player.hit(hit_amount, self, type)
                elif contained.id == loaders.GrenadePacket.id:
                    if check_nan(contained.value) or check_nan(*contained.position) or check_nan(*contained.velocity):
                        self.on_hack_attempt("Invalid grenade data")
                        return
                    if not self.grenades:
                        return
                    self.grenades -= 1
                    if not self.is_valid_position(*contained.position):
                        contained.position = self.world_object.position.get()
                    if self.on_grenade(contained.value) == False:
                        return
                    grenade = self.protocol.world.create_object(
                        world.Grenade, contained.value,
                        Vertex3(*contained.position), None,
                        Vertex3(*contained.velocity), self.grenade_exploded)
                    grenade.team = self.team
                    self.on_grenade_thrown(grenade)
                    if self.filter_visibility_data:
                        return
                    contained.player_id = self.player_id
                    self.protocol.send_contained(contained,
                        sender = self)
                elif contained.id == loaders.SetTool.id:
                    if self.on_tool_set_attempt(contained.value) == False:
                        return
                    old_tool = self.tool
                    self.tool = contained.value
                    if old_tool == WEAPON_TOOL:
                        self.weapon_object.set_shoot(False)
                    if self.tool == WEAPON_TOOL:
                        self.on_shoot_set(self.world_object.primary_fire)
                        self.weapon_object.set_shoot(
                            self.world_object.primary_fire)
                    self.world_object.set_weapon(self.tool == WEAPON_TOOL)
                    self.on_tool_changed(self.tool)
                    if self.filter_visibility_data or self.filter_animation_data:
                        return
                    set_tool.player_id = self.player_id
                    set_tool.value = contained.value
                    self.protocol.send_contained(set_tool, sender = self)
                elif contained.id == loaders.SetColor.id:
                    color = get_color(contained.value)
                    if self.on_color_set_attempt(color) == False:
                        return
                    self.color = color
                    self.on_color_set(color)
                    if self.filter_animation_data:
                        return
                    contained.player_id = self.player_id
                    self.protocol.send_contained(contained, sender = self,
                        save = True)
                elif contained.id == loaders.BlockAction.id:
                    value = contained.value
                    if value == BUILD_BLOCK:
                        interval = TOOL_INTERVAL[BLOCK_TOOL]
                    elif self.tool == WEAPON_TOOL:
                        if self.weapon_object.is_empty():
                            return
                        interval = WEAPON_INTERVAL[self.weapon]
                    else:
                        interval = TOOL_INTERVAL[self.tool]
                    current_time = reactor.seconds()
                    last_time = self.last_block
                    self.last_block = current_time
                    if (self.rapid_hack_detect and last_time is not None and
                        current_time - last_time < interval):
                        self.rapids.add(current_time)
                        if self.rapids.check():
                            start, end = self.rapids.get()
                            if end - start < MAX_RAPID_SPEED:
                                print 'RAPID HACK:', self.rapids.window
                                self.on_hack_attempt('Rapid hack detected')
                        return
                    map = self.protocol.map
                    x = contained.x
                    y = contained.y
                    z = contained.z
                    if z >= 62:
                        return
                    if value == BUILD_BLOCK:
                        self.blocks -= 1
                        pos = world_object.position
                        if self.blocks < -BUILD_TOLERANCE:
                            return
                        elif not collision_3d(pos.x, pos.y, pos.z, x, y, z,
                            MAX_BLOCK_DISTANCE):
                            return
                        elif self.on_block_build_attempt(x, y, z) == False:
                            return
                        elif not map.build_point(x, y, z, self.color):
                            return
                        self.on_block_build(x, y, z)
                    else:
                        if not map.get_solid(x, y, z):
                            return
                        pos = world_object.position
                        if self.tool == SPADE_TOOL and not collision_3d(
                            pos.x, pos.y, pos.z, x, y, z, MAX_DIG_DISTANCE):
                            return
                        if self.on_block_destroy(x, y, z, value) == False:
                            return
                        elif value == DESTROY_BLOCK:
                            if map.destroy_point(x, y, z):
                                self.blocks = min(50, self.blocks + 1)
                                self.on_block_removed(x, y, z)
                        elif value == SPADE_DESTROY:
                            if map.destroy_point(x, y, z):
                                self.on_block_removed(x, y, z)
                            if map.destroy_point(x, y, z + 1):
                                self.on_block_removed(x, y, z + 1)
                            if map.destroy_point(x, y, z - 1):
                                self.on_block_removed(x, y, z - 1)
                        self.last_block_destroy = reactor.seconds()
                    block_action.x = x
                    block_action.y = y
                    block_action.z = z
                    block_action.value = contained.value
                    block_action.player_id = self.player_id
                    self.protocol.send_contained(block_action, save = True)
                    self.protocol.update_entities()
                elif contained.id == loaders.BlockLine.id:
                    x1, y1, z1 = (contained.x1, contained.y1, contained.z1)
                    x2, y2, z2 = (contained.x2, contained.y2, contained.z2)
                    pos = world_object.position
                    if not collision_3d(pos.x, pos.y, pos.z, x2, y2, z2,
                                        MAX_BLOCK_DISTANCE):
                        return
                    points = world.cube_line(x1, y1, z1, x2, y2, z2)
                    if not points:
                        return
                    if len(points) > (self.blocks + BUILD_TOLERANCE):
                        return
                    map = self.protocol.map
                    if self.on_line_build_attempt(points) == False:
                        return
                    for point in points:
                        x, y, z = point
                        if not map.build_point(x, y, z, self.color):
                            break
                    self.blocks -= len(points)
                    self.on_line_build(points)
                    contained.player_id = self.player_id
                    self.protocol.send_contained(contained, save = True)
                    self.protocol.update_entities()
            if self.name:
                if contained.id == loaders.ChatMessage.id:
                    if not self.name:
                        return
                    value = contained.value
                    if value.startswith('/'):
                        self.on_command(*parse_command(value[1:]))
                    else:
                        global_message = contained.chat_type == CHAT_ALL
                        result = self.on_chat(value, global_message)
                        if result == False:
                            return
                        elif result is not None:
                            value = result
                        contained.chat_type = [CHAT_TEAM, CHAT_ALL][
                            int(global_message)]
                        contained.value = value
                        contained.player_id = self.player_id
                        if global_message:
                            team = None
                        else:
                            team = self.team
                        self.protocol.send_contained(contained, team = team)
                        self.on_chat_sent(value, global_message)
                elif contained.id == loaders.FogColor.id:
                    color = get_color(contained.color)
                    self.on_command('fog', [str(item) for item in color])
                elif contained.id == loaders.ChangeWeapon.id:
                    if self.on_weapon_set(contained.weapon) == False:
                        return
                    self.weapon = contained.weapon
                    self.set_weapon(self.weapon)
                elif contained.id == loaders.ChangeTeam.id:
                    team = self.protocol.teams[contained.team]
                    if self.on_team_join(team) == False:
                        return
                    self.set_team(team)

    def is_valid_position(self, x, y, z, distance = None):
        if not self.speedhack_detect:
            return True
        if distance is None:
            distance = RUBBERBAND_DISTANCE
        position = self.world_object.position
        return (math.fabs(x - position.x) < distance and
                math.fabs(y - position.y) < distance and
                math.fabs(z - position.z) < distance)

    def check_refill(self):
        last_refill = self.last_refill
        if (last_refill is None or
        reactor.seconds() - last_refill > self.protocol.refill_interval):
            self.last_refill = reactor.seconds()
            if self.on_refill() != False:
                self.refill()

    def get_location(self):
        position = self.world_object.position
        return position.x, position.y, position.z

    def is_location_free(self, x, y, z):
        return (self.protocol.map.get_solid(x, y, z) == 0 and
                self.protocol.map.get_solid(x, y, z + 1) == 0 and
                self.protocol.map.get_solid(x, y, z + 2) == 0 and
                self.protocol.map.get_solid(x, y, z + 3) == 1)

    def set_location_safe(self, location, center = True):
        x, y, z = location

        if center:
            x -= 0.5
            y -= 0.5
            z += 0.5
        x = int(x)
        y = int(y)
        z = int(z)

        # search for valid locations near the specified point
        modpos = 0
        pos_table = self.protocol.pos_table
        while (modpos<len(pos_table) and not
               self.is_location_free(x + pos_table[modpos][0],
                                     y + pos_table[modpos][1],
                                     z + pos_table[modpos][2])):
            modpos+=1
        if modpos == len(pos_table): # nothing nearby
            return
        x = x + pos_table[modpos][0]
        y = y + pos_table[modpos][1]
        z = z + pos_table[modpos][2]
        self.set_location((x, y, z))

    def set_location(self, location = None):
        if location is None:
            # used for rubberbanding
            position = self.world_object.position
            x, y, z = position.x, position.y, position.z
        else:
            x, y, z = location
            if self.world_object is not None:
                self.world_object.set_position(x, y, z)
            x += 0.5
            y += 0.5
            z -= 0.5
        position_data.x = x
        position_data.y = y
        position_data.z = z
        self.send_contained(position_data)

    def refill(self, local = False):
        self.hp = 100
        self.grenades = 3
        self.blocks = 50
        self.weapon_object.restock()
        if not local:
            self.send_contained(restock)

    def respawn(self):
        if self.spawn_call is None:
            self.spawn_call = reactor.callLater(
                self.get_respawn_time(), self.spawn)

    def get_spawn_location(self):
        game_mode = self.protocol.game_mode
        if game_mode == TC_MODE:
            try:
                base = random.choice(list(self.team.get_entities()))
                return base.get_spawn_location()
            except IndexError:
                pass
        return self.team.get_random_location(True)

    def get_respawn_time(self):
        if not self.respawn_time:
            return 0
        if self.protocol.respawn_waves:
            offset = reactor.seconds() % self.respawn_time
        else:
            offset = 0
        return self.respawn_time - offset

    def spawn(self, pos = None):
        self.spawn_call = None
        if self.team is None:
            return
        spectator = self.team.spectator
        if not spectator:
            if pos is None:
                x, y, z = self.get_spawn_location()
                x += 0.5
                y += 0.5
                z -= 2.4
            else:
                x, y, z = pos
            returned = self.on_spawn_location((x, y, z))
            if returned is not None:
                x, y, z = returned
            if self.world_object is not None:
                self.world_object.set_position(x, y, z, True)
            else:
                position = Vertex3(x, y, z)
                self.world_object = self.protocol.world.create_object(
                    world.Character, position, None, self._on_fall)
            self.world_object.dead = False
            self.tool = WEAPON_TOOL
            self.refill(True)
            create_player.x = x
            create_player.y = y
            create_player.z = z
            create_player.weapon = self.weapon
        create_player.player_id = self.player_id
        create_player.name = self.name
        create_player.team = self.team.id
        if self.filter_visibility_data and not spectator:
            self.send_contained(create_player)
        else:
            self.protocol.send_contained(create_player, save = True)
        if not spectator:
            self.on_spawn((x, y, z))

    def take_flag(self):
        if not self.hp:
            return
        flag = self.team.other.flag
        if flag.player is not None:
            return
        if self.on_flag_take() == False:
            return
        flag.player = self
        intel_pickup.player_id = self.player_id
        self.protocol.send_contained(intel_pickup, save = True)

    def capture_flag(self):
        other_team = self.team.other
        flag = other_team.flag
        player = flag.player
        if player is not self:
            return
        self.add_score(10) # 10 points for intel
        if (self.protocol.max_score not in (0, None) and
        self.team.score + 1 >= self.protocol.max_score):
            self.on_flag_capture()
            self.protocol.reset_game(self)
            self.protocol.on_game_end()
        else:
            intel_capture.player_id = self.player_id
            intel_capture.winning = False
            self.protocol.send_contained(intel_capture, save = True)
            self.team.score += 1
            flag = other_team.set_flag()
            flag.update()
            self.on_flag_capture()

    def drop_flag(self):
        protocol = self.protocol
        game_mode = protocol.game_mode
        if game_mode == CTF_MODE:
            for flag in (protocol.blue_team.flag, protocol.green_team.flag):
                player = flag.player
                if player is not self:
                    continue
                position = self.world_object.position
                x = int(position.x)
                y = int(position.y)
                z = max(0, int(position.z))
                z = self.protocol.map.get_z(x, y, z)
                flag.set(x, y, z)
                flag.player = None
                intel_drop.player_id = self.player_id
                intel_drop.x = flag.x
                intel_drop.y = flag.y
                intel_drop.z = flag.z
                self.protocol.send_contained(intel_drop, save = True)
                self.on_flag_drop()
                break
        elif game_mode == TC_MODE:
            for entity in protocol.entities:
                if self in entity.players:
                    entity.remove_player(self)

    def on_disconnect(self):
        if self.name is not None:
            self.drop_flag()
            player_left.player_id = self.player_id
            self.protocol.send_contained(player_left, sender = self,
                save = True)
            del self.protocol.players[self]
        if self.player_id is not None:
            self.protocol.player_ids.put_back(self.player_id)
            self.protocol.update_master()
        self.reset()

    def reset(self):
        if self.spawn_call is not None:
            self.spawn_call.cancel()
            self.spawn_call = None
        if self.world_object is not None:
            self.world_object.delete()
            self.world_object = None
        if self.team is not None:
            old_team = self.team
            self.team = None
            self.on_team_changed(old_team)
        self.on_reset()
        self.name = self.hp = self.world_object = None

    def hit(self, value, by = None, type = WEAPON_KILL):
        if self.hp is None:
            return
        if by is not None and self.team is by.team:
            friendly_fire = self.protocol.friendly_fire
            if friendly_fire == 'on_grief':
                if (type == MELEE_KILL and
                    not self.protocol.spade_teamkills_on_grief):
                    return
                hit_time = self.protocol.friendly_fire_time
                if (self.last_block_destroy is None
                or reactor.seconds() - self.last_block_destroy >= hit_time):
                    return
            elif not friendly_fire:
                return
        self.set_hp(self.hp - value, by, type = type)

    def set_hp(self, value, hit_by = None, type = WEAPON_KILL,
               hit_indicator = None, grenade = None):
        value = int(value)
        self.hp = max(0, min(100, value))
        if self.hp <= 0:
            self.kill(hit_by, type, grenade)
            return
        set_hp.hp = self.hp
        set_hp.not_fall = int(type != FALL_KILL)
        if hit_indicator is None:
            if hit_by is not None and hit_by is not self:
                hit_indicator = hit_by.world_object.position.get()
            else:
                hit_indicator = (0, 0, 0)
        x, y, z = hit_indicator
        set_hp.source_x = x
        set_hp.source_y = y
        set_hp.source_z = z
        self.send_contained(set_hp)

    def set_weapon(self, weapon, local = False, no_kill = False):
        self.weapon = weapon
        if self.weapon_object is not None:
            self.weapon_object.reset()
        self.weapon_object = WEAPONS[weapon](self._on_reload)
        if not local:
            self.protocol.send_contained(change_weapon, save = True)
            if not no_kill:
                self.kill(type = CLASS_CHANGE_KILL)

    def set_team(self, team):
        if team is self.team:
            return
        self.drop_flag()
        old_team = self.team
        self.team = team
        self.on_team_changed(old_team)
        if old_team.spectator:
            self.respawn()
        else:
            self.kill(type = TEAM_CHANGE_KILL)

    def kill(self, by = None, type = WEAPON_KILL, grenade = None):
        if self.hp is None:
            return
        if self.on_kill(by, type, grenade) is False:
            return
        self.drop_flag()
        self.hp = None
        self.weapon_object.reset()
        kill_action.kill_type = type
        if by is None:
            kill_action.killer_id = kill_action.player_id = self.player_id
        else:
            kill_action.killer_id = by.player_id
            kill_action.player_id = self.player_id
        if by is not None and by is not self:
            by.add_score(1)
        kill_action.respawn_time = self.get_respawn_time() + 1
        self.protocol.send_contained(kill_action, save = True)
        self.world_object.dead = True
        self.respawn()

    def add_score(self, score):
        self.kills += score

    def _connection_ack(self):
        self._send_connection_data()
        self.send_map(ProgressiveMapGenerator(self.protocol.map))

    def _send_connection_data(self):
        saved_loaders = self.saved_loaders = []
        if self.player_id is None:
            for player in self.protocol.players.values():
                if player.name is None:
                    continue
                existing_player.name = player.name
                existing_player.player_id = player.player_id
                existing_player.tool = player.tool or 0
                existing_player.weapon = player.weapon
                existing_player.kills = player.kills
                existing_player.team = player.team.id
                existing_player.color = make_color(*player.color)
                saved_loaders.append(existing_player.generate())

            self.player_id = self.protocol.player_ids.pop()
            self.protocol.update_master()

        # send initial data
        blue = self.protocol.blue_team
        green = self.protocol.green_team

        state_data.player_id = self.player_id
        state_data.fog_color = self.protocol.fog_color
        state_data.team1_color = blue.color
        state_data.team1_name = blue.name
        state_data.team2_color = green.color
        state_data.team2_name = green.name

        game_mode = self.protocol.game_mode

        if game_mode == CTF_MODE:
            blue_base = blue.base
            blue_flag = blue.flag
            green_base = green.base
            green_flag = green.flag
            ctf_data.cap_limit = self.protocol.max_score
            ctf_data.team1_score = blue.score
            ctf_data.team2_score = green.score

            ctf_data.team1_base_x = blue_base.x
            ctf_data.team1_base_y = blue_base.y
            ctf_data.team1_base_z = blue_base.z

            ctf_data.team2_base_x = green_base.x
            ctf_data.team2_base_y = green_base.y
            ctf_data.team2_base_z = green_base.z

            if green_flag.player is None:
                ctf_data.team1_has_intel = 0
                ctf_data.team2_flag_x = green_flag.x
                ctf_data.team2_flag_y = green_flag.y
                ctf_data.team2_flag_z = green_flag.z
            else:
                ctf_data.team1_has_intel = 1
                ctf_data.team2_carrier = green_flag.player.player_id

            if blue_flag.player is None:
                ctf_data.team2_has_intel = 0
                ctf_data.team1_flag_x = blue_flag.x
                ctf_data.team1_flag_y = blue_flag.y
                ctf_data.team1_flag_z = blue_flag.z
            else:
                ctf_data.team2_has_intel = 1
                ctf_data.team1_carrier = blue_flag.player.player_id

            state_data.state = ctf_data

        elif game_mode == TC_MODE:
            state_data.state = tc_data

        generated_data = state_data.generate()
        saved_loaders.append(generated_data)

    def grenade_exploded(self, grenade):
        if self.name is None or self.team.spectator:
            return
        if grenade.team is not None and grenade.team is not self.team:
            # could happen if the player changed team
            return
        position = grenade.position
        x = position.x
        y = position.y
        z = position.z
        if x < 0 or x > 512 or y < 0 or y > 512 or z < 0 or z > 63:
            return
        x = int(x)
        y = int(y)
        z = int(z)
        for player_list in (self.team.other.get_players(), (self,)):
            for player in player_list:
                if not player.hp:
                    continue
                damage = grenade.get_damage(player.world_object.position)
                if damage == 0:
                    continue
                returned = self.on_hit(damage, player, GRENADE_KILL, grenade)
                if returned == False:
                    continue
                elif returned is not None:
                    damage = returned
                player.set_hp(player.hp - damage, self,
                    hit_indicator = position.get(), type = GRENADE_KILL,
                    grenade = grenade)
        if self.on_block_destroy(x, y, z, GRENADE_DESTROY) == False:
            return
        map = self.protocol.map
        for nade_x in xrange(x - 1, x + 2):
            for nade_y in xrange(y - 1, y + 2):
                for nade_z in xrange(z - 1, z + 2):
                    if map.destroy_point(nade_x, nade_y, nade_z):
                        self.on_block_removed(nade_x, nade_y, nade_z)
        block_action.x = x
        block_action.y = y
        block_action.z = z
        block_action.value = GRENADE_DESTROY
        block_action.player_id = self.player_id
        self.protocol.send_contained(block_action, save = True)
        self.protocol.update_entities()

    def _on_fall(self, damage):
        if not self.hp:
            return
        returned = self.on_fall(damage)
        if returned == False:
            return
        elif returned is not None:
            damage = returned
        self.set_hp(self.hp - damage, type = FALL_KILL)

    def _on_reload(self):
        weapon_reload.player_id = self.player_id
        weapon_reload.clip_ammo = self.weapon_object.current_ammo
        weapon_reload.reserve_ammo = self.weapon_object.current_stock
        self.send_contained(weapon_reload)

    def send_map(self, data = None):
        if data is not None:
            self.map_data = data
            map_start.size = data.get_size()
            self.send_contained(map_start)
        elif self.map_data is None:
            return

        if not self.map_data.data_left():
            self.map_data = None
            for data in self.saved_loaders:
                packet = enet.Packet(str(data), enet.PACKET_FLAG_RELIABLE)
                self.peer.send(0, packet)
            self.saved_loaders = None
            self.on_join()
            return
        for _ in xrange(10):
            if not self.map_data.data_left():
                break
            map_data.data = self.map_data.read(1024)
            self.send_contained(map_data)

    def continue_map_transfer(self):
        self.send_map()

    def send_data(self, data):
        self.protocol.transport.write(data, self.address)

    def send_chat(self, value, global_message = None):
        if self.deaf:
            return
        if global_message is None:
            chat_message.chat_type = CHAT_SYSTEM
            prefix = ''
        else:
            chat_message.chat_type = CHAT_TEAM
            # 34 is guaranteed to be out of range!
            chat_message.player_id = 35
            prefix = self.protocol.server_prefix + ' '
        lines = textwrap.wrap(value, MAX_CHAT_SIZE - len(prefix) - 1)
        for line in lines:
            chat_message.value = '%s%s' % (prefix, line)
            self.send_contained(chat_message)

    # events/hooks

    def on_join(self):
        pass

    def on_login(self, name):
        pass

    def on_spawn(self, pos):
        pass

    def on_spawn_location(self, pos):
        pass

    def on_chat(self, value, global_message):
        pass

    def on_chat_sent(self, value, global_message):
        pass

    def on_command(self, command, parameters):
        pass

    def on_hit(self, hit_amount, hit_player, type, grenade):
        pass

    def on_kill(self, killer, type, grenade):
        pass

    def on_team_join(self, team):
        pass

    def on_team_changed(self, old_team):
        pass

    def on_tool_set_attempt(self, tool):
        pass

    def on_tool_changed(self, tool):
        pass

    def on_grenade(self, time_left):
        pass

    def on_grenade_thrown(self, grenade):
        pass

    def on_block_build_attempt(self, x, y, z):
        pass

    def on_block_build(self, x, y, z):
        pass

    def on_line_build_attempt(self, points):
        pass

    def on_line_build(self, points):
        pass

    def on_block_destroy(self, x, y, z, mode):
        pass

    def on_block_removed(self, x, y, z):
        pass

    def on_refill(self):
        pass

    def on_color_set_attempt(self, color):
        pass

    def on_color_set(self, color):
        pass

    def on_flag_take(self):
        pass

    def on_flag_capture(self):
        pass

    def on_flag_drop(self):
        pass

    def on_hack_attempt(self, reason):
        pass

    def on_position_update(self):
        pass

    def on_weapon_set(self, value):
        pass

    def on_fall(self, damage):
        pass

    def on_reset(self):
        pass

    def on_orientation_update(self, x, y, z):
        pass

    def on_shoot_set(self, fire):
        pass

    def on_secondary_fire_set(self, secondary):
        pass

    def on_walk_update(self, up, down, left, right):
        pass

    def on_animation_update(self, jump, crouch, sneak, sprint):
        pass

class Entity(Vertex3):
    team = None
    def __init__(self, id, protocol, *arg, **kw):
        Vertex3.__init__(self, *arg, **kw)
        self.id = id
        self.protocol = protocol

    def update(self):
        move_object.object_type = self.id
        if self.team is None:
            state = NEUTRAL_TEAM
        else:
            state = self.team.id
        move_object.state = state
        move_object.x = self.x
        move_object.y = self.y
        move_object.z = self.z
        self.protocol.send_contained(move_object, save = True)

class Flag(Entity):
    player = None

    def update(self):
        if self.player is not None:
            return
        Entity.update(self)

class Territory(Flag):
    progress = 0.0
    players = None
    start = None
    rate = 0
    rate_value = 0.0
    finish_call = None
    capturing_team = None

    def __init__(self, *arg, **kw):
        Flag.__init__(self, *arg, **kw)
        self.players = set()

    def add_player(self, player):
        self.get_progress(True)
        self.players.add(player)
        self.update_rate()

    def remove_player(self, player):
        self.get_progress(True)
        self.players.discard(player)
        self.update_rate()

    def update_rate(self):
        rate = 0
        for player in self.players:
            if player.team.id:
                rate += 1
            else:
                rate -= 1
        progress = self.progress
        if ((progress == 1.0 and (rate > 0 or rate == 0)) or
           (progress == 0.0 and (rate < 0 or rate == 0))):
            return
        self.rate = rate
        self.rate_value = rate * TC_CAPTURE_RATE
        if self.finish_call is not None:
            self.finish_call.cancel()
            self.finish_call = None
        if rate != 0:
            self.start = reactor.seconds()
            rate_value = self.rate_value
            if rate_value < 0:
                self.capturing_team = self.protocol.blue_team
                end_time = progress / -rate_value
            else:
                self.capturing_team = self.protocol.green_team
                end_time = (1.0 - progress) / rate_value
            if self.capturing_team is not self.team:
                self.finish_call = reactor.callLater(end_time, self.finish)
        self.send_progress()

    def send_progress(self):
        progress_bar.object_index = self.id
        if self.team is None:
            capturing_team = self.capturing_team
            team = capturing_team.other
        else:
            capturing_team = self.team.other
            team = self.team
        progress_bar.capturing_team = capturing_team.id
        rate = self.rate
        progress = self.get_progress()
        if team.id:
            rate = -rate
            progress = 1 - progress
        progress_bar.progress = progress
        progress_bar.rate = rate
        self.protocol.send_contained(progress_bar)

    def finish(self):
        self.finish_call = None
        protocol = self.protocol
        if self.rate > 0:
            team = protocol.green_team
        else:
            team = protocol.blue_team
        team.score += 1
        if self.team is not None:
            self.team.score -= 1
        self.team = team
        protocol.on_cp_capture(self)
        if team.score >= protocol.max_score:
            protocol.reset_game(territory = self)
            protocol.on_game_end()
        else:
            territory_capture.object_index = self.id
            territory_capture.state = self.team.id
            territory_capture.winning = False
            protocol.send_contained(territory_capture)

    def get_progress(self, set = False):
        """
        Return progress (between 0 and 1 - 0 is full blue control, 1 is full
        green control) and optionally set the current progress.
        """
        rate = self.rate_value
        start = self.start
        if rate == 0.0 or start is None:
            return self.progress
        dt = reactor.seconds() - start
        progress = max(0, min(1, self.progress + rate * dt))
        if set:
            self.progress = progress
        return progress

    def get_spawn_location(self):
        x1 = max(0, self.x - SPAWN_RADIUS)
        y1 = max(0, self.y - SPAWN_RADIUS)
        x2 = min(512, self.x + SPAWN_RADIUS)
        y2 = min(512, self.y + SPAWN_RADIUS)
        return self.protocol.get_random_location(True, (x1, y1, x2, y2))

class Base(Entity):
    pass

class Team(object):
    score = None
    flag = None
    base = None
    other = None
    protocol = None
    name = None
    kills = None

    def __init__(self, id, name, color, spectator, protocol):
        self.id = id
        self.name = name
        self.protocol = protocol
        self.color = color
        self.spectator = spectator

    def get_players(self):
        for player in self.protocol.players.values():
            if player.team is self:
                yield player

    def count(self):
        count = 0
        for player in self.protocol.players.values():
            if player.team is self:
                count += 1
        return count

    def initialize(self):
        if self.spectator:
            return
        self.score = 0
        self.kills = 0
        if self.protocol.game_mode == CTF_MODE:
            self.set_flag()
            self.set_base()

    def set_flag(self):
        entity_id = [BLUE_FLAG, GREEN_FLAG][self.id]
        if self.flag is None:
            self.flag = Flag(entity_id, self.protocol)
            self.flag.team = self
            self.protocol.entities.append(self.flag)
        location = self.get_entity_location(entity_id)
        returned = self.protocol.on_flag_spawn(location[0], location[1],
                        location[2], self.flag, entity_id)
        if returned is not None:
            location = returned
        self.flag.set(*location)
        self.flag.player = None
        return self.flag

    def set_base(self):
        entity_id = [BLUE_BASE, GREEN_BASE][self.id]
        if self.base is None:
            self.base = Base(entity_id, self.protocol)
            self.base.team = self
            self.protocol.entities.append(self.base)
        location = self.get_entity_location(entity_id)
        returned = self.protocol.on_base_spawn(location[0], location[1],
                        location[2], self.base, entity_id)
        if returned is not None:
            location = returned
        self.base.set(*location)
        return self.base

    def get_entity_location(self, entity_id):
        return self.get_random_location(True)

    def get_random_location(self, force_land = False):
        x_offset = self.id * 384
        return self.protocol.get_random_location(force_land, (
            x_offset, 128, 128 + x_offset, 384))

    def get_entities(self):
        for item in self.protocol.entities:
            if item.team is self:
                yield item

class ServerProtocol(BaseProtocol):
    connection_class = ServerConnection

    name = 'pyspades server'
    game_mode = CTF_MODE
    max_players = 32
    connections = None
    player_ids = None
    master = False
    max_score = 10
    map = None
    spade_teamkills_on_grief = False
    friendly_fire = False
    friendly_fire_time = 2
    server_prefix = '[*]'
    respawn_time = 5
    refill_interval = 20
    master_connection = None
    speedhack_detect = True
    fog_color = (128, 232, 255)
    winning_player = None
    world = None
    team_class = Team
    team1_color = (0, 0, 196)
    team2_color = (0, 196, 0)
    team1_name = 'Blue'
    team2_name = 'Green'
    spectator_name = 'Spectator'
    loop_count = 0
    melee_damage = 100
    version = GAME_VERSION
    respawn_waves = False

    def __init__(self, *arg, **kw):
        # +2 to allow server->master and master->server connection since enet
        # allocates peers for both clients and hosts. this is done at
        # enet-level, not application-level, so even for masterless-servers,
        # this should not allow additional players.
        self.max_connections = self.max_players + 2
        BaseProtocol.__init__(self, *arg, **kw)
        self.entities = []
        self.players = MultikeyDict()
        self.player_ids = IDPool()
        self.spectator_team = self.team_class(-1, self.spectator_name,
            (0, 0, 0), True, self)
        self.blue_team = self.team_class(0, self.team1_name, self.team1_color,
            False, self)
        self.green_team = self.team_class(1, self.team2_name, self.team2_color,
            False, self)
        self.teams = {
            -1 : self.spectator_team,
            0 : self.blue_team,
            1 : self.green_team
        }
        self.blue_team.other = self.green_team
        self.green_team.other = self.blue_team
        self.world = world.World()
        self.set_master()

        # safe position LUT
        self.pos_table = []
        for x in xrange(-5,6):
            for y in xrange(-5,6):
                for z in xrange(-5,6):
                    self.pos_table.append((x,y,z))
        self.pos_table.sort(key=lambda vec: abs(vec[0]*1.03) +\
                                            abs(vec[1]*1.02) +\
                                            abs(vec[2]*1.01))

    def send_contained(self, contained, unsequenced = False, sender = None,
                       team = None, save = False, rule = None):
        if unsequenced:
            flags = enet.PACKET_FLAG_UNSEQUENCED
        else:
            flags = enet.PACKET_FLAG_RELIABLE
        data = ByteWriter()
        contained.write(data)
        data = str(data)
        packet = enet.Packet(data, flags)
        for player in self.connections.values():
            if player is sender or player.player_id is None:
                continue
            if team is not None and player.team is not team:
                continue
            if rule is not None and rule(player) == False:
                continue
            if player.saved_loaders is not None:
                if save:
                    player.saved_loaders.append(data)
            else:
                player.peer.send(0, packet)

    def reset_tc(self):
        self.entities = self.get_cp_entities()
        for entity in self.entities:
            team = entity.team
            if team is None:
                entity.progress = 0.5
            else:
                team.score += 1
                entity.progress = float(team.id)
        tc_data.set_entities(self.entities)
        self.max_score = len(self.entities)

    def get_cp_entities(self):
        # cool algorithm number 1
        entities = []
        land_count = self.map.count_land(0, 0, 512, 512)
        territory_count = int((land_count/(512.0 * 512.0))*(
            MAX_TERRITORY_COUNT-MIN_TERRITORY_COUNT) + MIN_TERRITORY_COUNT)
        j = 512.0 / territory_count
        for i in xrange(territory_count):
            x1 = i * j
            y1 = 512 / 4
            x2 = (i + 1) * j
            y2 = y1 * 3
            flag = Territory(i, self, *self.get_random_location(
                zone = (x1, y1, x2, y2)))
            if i < territory_count / 2:
                team = self.blue_team
            elif i > (territory_count-1) / 2:
                team = self.green_team
            else:
                # odd number - neutral
                team = None
            flag.team = team
            entities.append(flag)
        return entities

    def update(self):
        self.loop_count += 1
        BaseProtocol.update(self)
        for player in self.connections.values():
            if (player.map_data is not None and
            not player.peer.reliableDataInTransit):
                player.continue_map_transfer()
        self.world.update(UPDATE_FREQUENCY)
        self.on_world_update()
        if self.loop_count % int(UPDATE_FPS / NETWORK_FPS) == 0:
            self.update_network()

    def update_network(self):
        items = []
        for i in xrange(32):
            position = orientation = None
            try:
                player = self.players[i]
                if (not player.filter_visibility_data and
                not player.team.spectator):
                    world_object = player.world_object
                    position = world_object.position.get()
                    orientation = world_object.orientation.get()
            except (KeyError, TypeError, AttributeError):
                pass
            if position is None:
                position = (0.0, 0.0, 0.0)
                orientation = (0.0, 0.0, 0.0)
            items.append((position, orientation))
        world_update.items = items
        self.send_contained(world_update, unsequenced = True)

    def set_map(self, map):
        self.map = map
        self.world.map = map
        self.on_map_change(map)
        self.blue_team.initialize()
        self.green_team.initialize()
        if self.game_mode == TC_MODE:
            self.reset_tc()
        self.players = MultikeyDict()
        if self.connections:
            data = ProgressiveMapGenerator(self.map, parent = True)
            for connection in self.connections.values():
                if connection.player_id is None:
                    continue
                if connection.map_data is not None:
                    connection.disconnect()
                    continue
                connection.reset()
                connection._send_connection_data()
                connection.send_map(data.get_child())
        self.update_entities()

    def reset_game(self, player = None, territory = None):
        blue_team = self.blue_team
        green_team = self.green_team
        blue_team.initialize()
        green_team.initialize()
        if self.game_mode == CTF_MODE:
            if player is None:
                player = self.players.values()[0]
            intel_capture.player_id = player.player_id
            intel_capture.winning = True
            self.send_contained(intel_capture, save = True)
        elif self.game_mode == TC_MODE:
            if territory is None:
                territory = self.entities[0]
            territory_capture.object_index = territory.id
            territory_capture.winning = True
            territory_capture.state = territory.team.id
            self.send_contained(territory_capture)
            self.reset_tc()
        for entity in self.entities:
            entity.update()
        for player in self.players.values():
            if player.team is not None:
                player.spawn()

    def get_name(self, name):
        name = name.replace('%', '').encode('ascii', 'ignore')
        new_name = name
        names = [p.name.lower() for p in self.players.values()]
        i = 0
        while new_name.lower() in names:
            i += 1
            new_name = name + str(i)
        return new_name

    def get_mode_mode(self):
        if self.game_mode == CTF_MODE:
            return 'ctf'
        elif self.game_mode == TC_MODE:
            return 'tc'
        return 'unknown'

    def get_random_location(self, force_land = True, zone = (0, 0, 512, 512)):
        x1, y1, x2, y2 = zone
        if force_land:
            x, y = self.map.get_random_point(x1, y1, x2, y2)
        else:
            x = random.randrange(x1, x2)
            y = random.randrange(y1, y2)
        z = self.map.get_z(x, y)
        return x, y, z

    def set_master(self):
        if self.master:
            get_master_connection(self).addCallbacks(
                self.got_master_connection,
                self.master_disconnected)

    def got_master_connection(self, connection):
        self.master_connection = connection
        connection.disconnect_callback = self.master_disconnected
        self.update_master()

    def master_disconnected(self, client = None):
        self.master_connection = None

    def update_master(self):
        if self.master_connection is None:
            return
        count = 0
        for connection in self.connections.values():
            if connection.player_id is not None:
                count += 1
        self.master_connection.set_count(count)

    def update_entities(self):
        map = self.map
        for entity in self.entities:
            moved = False
            if map.get_solid(entity.x, entity.y, entity.z - 1):
                moved = True
                entity.z -= 1
                while map.get_solid(entity.x, entity.y, entity.z - 1):
                    entity.z -= 1
            else:
                while not map.get_solid(entity.x, entity.y, entity.z):
                    moved = True
                    entity.z += 1
            if moved or self.on_update_entity(entity):
                entity.update()

    def send_chat(self, value, global_message = None, sender = None,
                  team = None):
        for player in self.players.values():
            if player is sender:
                continue
            if player.deaf:
                continue
            if team is not None and player.team is not team:
                continue
            player.send_chat(value, global_message)

    def set_fog_color(self, color):
        self.fog_color = color
        fog_color.color = make_color(*color)
        self.send_contained(fog_color, save = True)

    def get_fog_color(self):
        return self.fog_color

    # events

    def on_cp_capture(self, cp):
        pass

    def on_game_end(self):
        pass

    def on_world_update(self):
        pass

    def on_map_change(self, map):
        pass

    def on_base_spawn(self, x, y, z, base, entity_id):
        pass

    def on_flag_spawn(self, x, y, z, flag, entity_id):
        pass

    def on_update_entity(self, entity):
        pass
