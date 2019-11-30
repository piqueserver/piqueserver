import collections
import math
import random
import re
import shlex
import textwrap
from itertools import product
from typing import Any, Dict, Optional, Sequence, Tuple, Union

import enet
from twisted.internet import reactor
from twisted.logger import Logger

from pyspades import contained as loaders
from pyspades import world
from pyspades.collision import collision_3d, vector_collision
from pyspades.common import Vertex3, get_color, make_color
from pyspades.constants import *
from pyspades.constants import (BLOCK_TOOL, CTF_MODE, ERROR_FULL,
                                ERROR_TOO_MANY_CONNECTIONS,
                                ERROR_WRONG_VERSION, FALL_KILL, HEAD,
                                HEADSHOT_KILL, HIT_TOLERANCE,
                                MAX_BLOCK_DISTANCE, MAX_POSITION_RATE, MELEE,
                                MELEE_DISTANCE, MELEE_KILL,
                                RAPID_WINDOW_ENTRIES, SPADE_TOOL,
                                TC_CAPTURE_DISTANCE, TC_MODE, WEAPON_KILL,
                                WEAPON_TOOL)
from pyspades.mapgenerator import ProgressiveMapGenerator
from pyspades.packet import call_packet_handler, register_packet_handler
from pyspades.protocol import BaseConnection
from pyspades.team import Team
from pyspades.weapon import WEAPONS

log = Logger()


tc_data = loaders.TCState()

def check_nan(*values) -> bool:
    for value in values:
        if math.isnan(value):
            return True
    return False


def parse_command(value: str) -> Tuple[str, Sequence[str]]:
    try:
        splitted = shlex.split(value)
    except ValueError:
        # shlex failed. let's just split per space
        splitted = value.split(' ')
    if splitted:
        command = splitted.pop(0)
    else:
        command = ''
    return command, splitted


class SlidingWindow:
    def __init__(self, entries: Any) -> None:
        self.entries = entries
        self.window = collections.deque()  # type: Deque

    def add(self, value) -> None:
        self.window.append(value)
        if len(self.window) <= self.entries:
            return
        self.window.popleft()

    def check(self) -> bool:
        return len(self.window) == self.entries

    def get(self) -> Any:
        return self.window[0], self.window[-1]


class ServerConnection(BaseConnection):
    address = None  # Tuple[int, int]
    player_id = None
    map_packets_sent = 0
    team = None  # type: Team
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
    rubberband_distance = 10
    rapid_hack_detect = False
    timers = None
    world_object = None  # type: world.Character
    last_block = None
    map_data = None
    last_position_update = None
    local = False

    def __init__(self, *arg, **kw) -> None:
        BaseConnection.__init__(self, *arg, **kw)
        protocol = self.protocol
        address = self.peer.address
        self.total_blocks_removed = 0
        self.address = (address.host, address.port)
        self.respawn_time = protocol.respawn_time
        self.rapids = SlidingWindow(RAPID_WINDOW_ENTRIES)
        self.client_info = {}
        self.proto_extensions = {}  # type: Dict[int, int]
        self.line_build_start_pos = None

    def on_connect(self) -> None:
        if self.local:
            return
        if self.peer.eventData != self.protocol.version:
            log.debug("{player} kicked: wrong protocol version {version}",
                      player=self, version=self.peer.eventData)
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
                self.disconnect(ERROR_TOO_MANY_CONNECTIONS)
                return
        if not self.disconnected:
            log.debug("sending map data to {player}", player=self)
            self._connection_ack()

    def loader_received(self, loader: enet.Packet) -> None:
        """
        called when a loader i.e. packet is received.
        calls the packet handler registered with
        @register_packet_handler
        """
        if self.player_id is None:
            return
        call_packet_handler(self, loader)

    @register_packet_handler(loaders.ProtocolExtensionInfo)
    def on_ext_info_received(self, contained: loaders.ProtocolExtensionInfo) -> None:
        self.proto_extensions = dict(contained.extensions)
        log.debug("received extinfo {extinfo} from {player}",
                  extinfo=self.proto_extensions,
                  player=self)

    @register_packet_handler(loaders.ExistingPlayer)
    @register_packet_handler(loaders.ShortPlayerData)
    def on_new_player_recieved(self, contained: loaders.ExistingPlayer) -> None:
        if self.team is not None and not self.team.spectator:
            # This player has already joined the game as a full player.
            # Existingplayer may only be sent if in the limbo or spectator
            # modes. Without this check, they could respawn themselves
            # instantly on any team they wanted.
            log.debug("{} tried sending an ExistingPlayer packet while not in"
                      " limbo or spectator mode".format(self))
            return

        old_team = self.team
        team = self.protocol.teams[contained.team]
        log.debug("{user} wants to join {team}",
                  user=self, team=team, teamid=contained.team)

        ret = self.on_team_join(team)
        if ret is False:
            team = self.protocol.team_spectator
        elif ret is not None:
            team = ret

        self.team = team
        if self.name is None:
            name = contained.name
            self.name = self.protocol.get_name(name)
            self.protocol.players[self.player_id] = self
            self.on_login(self.name)
        else:
            self.on_team_changed(old_team)
        self.set_weapon(contained.weapon, True)
        if self.protocol.speedhack_detect and not self.local:
            self.speedhack_detect = True
        if self.protocol.rubberband_distance is not None:
            self.rubberband_distance = self.protocol.rubberband_distance
        if not self.local:
            self.rapid_hack_detect = True
        if team.spectator:
            if self.world_object is not None:
                self.world_object.delete()
                self.world_object = None
        # send kill packets for dead players
        for player in self.protocol.players.values():
            if (player.player_id != self.player_id and player.world_object
                    and player.world_object.dead):
                kill_action = loaders.KillAction()
                kill_action.killer_id = player.player_id
                kill_action.player_id = player.player_id
                kill_action.kill_type = FALL_KILL
                self.send_contained(kill_action)

        self.spawn()

    @register_packet_handler(loaders.OrientationData)
    def on_orientation_update_recieved(self, contained: loaders.OrientationData) -> None:
        if not self.hp:
            return
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
        self.world_object.set_orientation(x, y, z)

    @register_packet_handler(loaders.PositionData)
    def on_position_update_recieved(self, contained: loaders.PositionData) -> None:
        if not self.hp:
            return
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
        if not self.check_speedhack(x, y, z):
            # vanilla behaviour
            self.set_location()
            return
        if not self.freeze_animation:
            self.world_object.set_position(x, y, z)
            self.on_position_update()
        if self.filter_visibility_data:
            return
        game_mode = self.protocol.game_mode
        if game_mode == CTF_MODE:
            other_flag = self.team.other.flag
            if vector_collision(self.world_object.position,
                                self.team.base):
                if other_flag.player is self:
                    self.capture_flag()
                self.check_refill()
            if other_flag.player is None and vector_collision(
                    self.world_object.position, other_flag):
                self.take_flag()
        elif game_mode == TC_MODE:
            for entity in self.protocol.entities:
                collides = vector_collision(
                    entity, self.world_object.position, TC_CAPTURE_DISTANCE)
                if self in entity.players:
                    if not collides:
                        entity.remove_player(self)
                else:
                    if collides:
                        entity.add_player(self)
                if collides and vector_collision(entity,
                                                 self.world_object.position):
                    self.check_refill()

    @register_packet_handler(loaders.WeaponInput)
    def on_weapon_input_recieved(self, contained: loaders.WeaponInput) -> None:
        if not self.hp:
            return
        primary = contained.primary
        secondary = contained.secondary
        if self.world_object.primary_fire != primary:
            # player has pressed or released primary fire
            if self.tool == WEAPON_TOOL:
                self.weapon_object.set_shoot(primary)
            if self.tool == WEAPON_TOOL or self.tool == SPADE_TOOL:
                self.on_shoot_set(primary)

        if self.world_object.secondary_fire != secondary:
            # player has pressed or released secondary fire
            self.on_secondary_fire_set(secondary)

            if secondary and self.tool == BLOCK_TOOL:
                # hook into here to save the start location of the line build.
                # This is needed so we can check if the player was actually at
                # the starting location of the line build when it was started.
                # this is inspired by 1AmYF's fbpatch2.py script
                position = self.world_object.position
                self.line_build_start_pos = position.copy()
                self.on_line_build_start()

        # remember the current state of the mouse buttons
        self.world_object.primary_fire = primary
        self.world_object.secondary_fire = secondary
        if self.filter_weapon_input:
            return
        contained.player_id = self.player_id
        self.protocol.send_contained(contained, sender=self)

    @register_packet_handler(loaders.InputData)
    def on_input_data_recieved(self, contained: loaders.InputData) -> None:
        if not self.hp:
            return
        world_object = self.world_object
        returned = self.on_walk_update(contained.up, contained.down,
                                       contained.left, contained.right)
        if returned is not None:
            up, down, left, right = returned
            if (up != contained.up or down != contained.down or
                    left != contained.left or right != contained.right):
                (contained.up, contained.down, contained.left,
                    contained.right) = returned
                # XXX unsupported
                # self.send_contained(contained)
        if not self.freeze_animation:
            world_object.set_walk(contained.up, contained.down,
                                  contained.left, contained.right)
        contained.player_id = self.player_id
        z_vel = world_object.velocity.z
        if contained.jump and not (z_vel >= 0 and z_vel < 0.017):
            contained.jump = False
        # XXX unsupported for now
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
        returned = self.on_animation_update(
            contained.jump, contained.crouch, contained.sneak,
            contained.sprint)
        if returned is not None:
            jump, crouch, sneak, sprint = returned
            if (jump != contained.jump or crouch != contained.crouch or
                    sneak != contained.sneak or sprint != contained.sprint):
                (contained.jump, contained.crouch, contained.sneak,
                    contained.sprint) = returned
                self.send_contained(contained)
        if not self.freeze_animation:
            world_object.set_animation(
                contained.jump, contained.crouch, contained.sneak,
                contained.sprint)
        if self.filter_visibility_data or self.filter_animation_data:
            return
        self.protocol.send_contained(contained, sender=self)

    @register_packet_handler(loaders.WeaponReload)
    def on_reload_recieved(self, contained) -> None:
        if not self.hp:
            return
        self.weapon_object.reload()
        if self.filter_animation_data:
            return
        contained.player_id = self.player_id
        self.protocol.send_contained(contained, sender=self)

    @register_packet_handler(loaders.HitPacket)
    def on_hit_recieved(self, contained):
        if not self.hp:
            return
        world_object = self.world_object
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
            kill_type = MELEE_KILL
        elif contained.value == HEAD:
            kill_type = HEADSHOT_KILL
        else:
            kill_type = WEAPON_KILL
        returned = self.on_hit(hit_amount, player, kill_type, None)
        if returned == False:
            return
        elif returned is not None:
            hit_amount = returned
        player.hit(hit_amount, self, kill_type)

    @register_packet_handler(loaders.GrenadePacket)
    def on_grenade_recieved(self, contained: loaders.GrenadePacket) -> None:
        if not self.hp:
            return
        if check_nan(contained.value, *contained.position) or check_nan(*contained.velocity):
            self.on_hack_attempt("Invalid grenade data")
            return
        if not self.grenades:
            return
        self.grenades -= 1
        if not self.check_speedhack(*contained.position):
            contained.position = self.world_object.position.get()
        if self.on_grenade(contained.value) == False:
            return
        grenade = self.protocol.world.create_object(
            world.Grenade, contained.value,
            Vertex3(*contained.position), None,
            Vertex3(*contained.velocity), self.grenade_exploded)
        grenade.team = self.team
        log.debug("{player!r} ({world_object!r}) created {grenade!r}",
                  grenade=grenade, world_object=self.world_object, player=self)
        self.on_grenade_thrown(grenade)
        if self.filter_visibility_data:
            return
        contained.player_id = self.player_id
        self.protocol.send_contained(contained,
                                     sender=self)

    @register_packet_handler(loaders.SetTool)
    def on_tool_change_recieved(self, contained: loaders.SetTool) -> None:
        if not self.hp:
            return
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
        set_tool = loaders.SetTool()
        set_tool.player_id = self.player_id
        set_tool.value = contained.value
        self.protocol.send_contained(set_tool, sender=self, save=True)

    @register_packet_handler(loaders.SetColor)
    def on_color_change_recieved(self, contained: loaders.SetColor) -> None:
        if not self.hp:
            return
        color = get_color(contained.value)
        if self.on_color_set_attempt(color) == False:
            return
        self.color = color
        self.on_color_set(color)
        if self.filter_animation_data:
            return
        contained.player_id = self.player_id
        self.protocol.send_contained(contained, sender=self,
                                     save=True)

    @register_packet_handler(loaders.BlockAction)
    def on_block_action_recieved(self, contained: loaders.BlockAction) -> None:
        world_object = self.world_object
        if not self.hp:
            return
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
                    log.info('RAPID HACK: {window}', window=self.rapids.window)
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
                count = map.destroy_point(x, y, z)
                if count:
                    self.total_blocks_removed += count
                    self.blocks = min(50, self.blocks + 1)
                    self.on_block_removed(x, y, z)
            elif value == SPADE_DESTROY:
                for xyz in ((x, y, z), (x, y, z + 1), (x, y, z - 1)):
                    count = map.destroy_point(*xyz)
                    if count:
                        self.total_blocks_removed += count
                        self.on_block_removed(*xyz)
            self.last_block_destroy = reactor.seconds()
        block_action = loaders.BlockAction()
        block_action.x = x
        block_action.y = y
        block_action.z = z
        block_action.value = contained.value
        block_action.player_id = self.player_id
        self.protocol.send_contained(block_action, save=True)
        self.protocol.update_entities()

    @register_packet_handler(loaders.BlockLine)
    def on_block_line_recieved(self, contained):
        if not self.hp:
            return  # dead players can't build

        map_ = self.protocol.map

        x1, y1, z1 = (contained.x1, contained.y1, contained.z1)
        x2, y2, z2 = (contained.x2, contained.y2, contained.z2)
        pos = self.world_object.position
        start_pos = self.line_build_start_pos

        if (not map_.is_valid_position(x1, y1, z1)
                or not map_.is_valid_position(x2, y2, z2)):
            return  # coordinates are out of bounds

        # ensure that the player is currently within tolerance of the location
        # that the line build ended at
        if not collision_3d(pos.x, pos.y, pos.z, x2, y2, z2,
                            MAX_BLOCK_DISTANCE):
            return

        # ensure that the player was within tolerance of the location
        # that the line build started at
        if not collision_3d(start_pos.x, start_pos.y, start_pos.z, x1, y1, z1,
                            MAX_BLOCK_DISTANCE):
            return

        points = world.cube_line(x1, y1, z1, x2, y2, z2)

        if not points:
            return

        if len(points) > (self.blocks + BUILD_TOLERANCE):
            return

        if self.on_line_build_attempt(points) is False:
            return

        for point in points:
            x, y, z = point
            if map_.get_solid(x, y, z):
                continue
            if not map_.build_point(x, y, z, self.color):
                break

        self.blocks -= len(points)
        self.on_line_build(points)
        contained.player_id = self.player_id
        self.protocol.send_contained(contained, save=True)
        self.protocol.update_entities()

    @register_packet_handler(loaders.ChatMessage)
    def on_chat_message_recieved(self, contained: loaders.ChatMessage) -> None:
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
            contained.chat_type = CHAT_ALL if global_message else CHAT_TEAM
            contained.value = value
            contained.player_id = self.player_id
            if global_message:
                team = None
            else:
                team = self.team
            for player in self.protocol.players.values():
                if not player.deaf:
                    if team is None or team is player.team:
                        player.send_contained(contained)
            self.on_chat_sent(value, global_message)

    @register_packet_handler(loaders.FogColor)
    def on_fog_color_recieved(self, contained):
        # FIXME: this theoretically might anyone to set the fog...
        # do we even need this?
        if not self.name:
            return
        color = get_color(contained.color)
        self.on_command('fog', [str(item) for item in color])

    @register_packet_handler(loaders.ChangeWeapon)
    def on_weapon_change_recieved(self, contained):
        if not self.name:
            return
        if self.on_weapon_set(contained.weapon) == False:
            return
        self.weapon = contained.weapon
        self.set_weapon(self.weapon)

    @register_packet_handler(loaders.ChangeTeam)
    def on_team_change_recieved(self, contained):
        if not self.name:
            return
        team = self.protocol.teams[contained.team]
        ret = self.on_team_join(team)
        if ret is False:
            return
        team = ret or team
        self.set_team(team)

    @register_packet_handler(loaders.HandShakeReturn)
    def on_handshake_recieved(self, contained: loaders.HandShakeReturn) -> None:
        version_request = loaders.VersionRequest()
        self.protocol.send_contained(version_request)

    @register_packet_handler(loaders.VersionResponse)
    def on_version_info_recieved(self, contained: loaders.VersionResponse) -> None:
        self.client_info["version"] = contained.version
        self.client_info["os_info"] = contained.os_info
        # TODO: Make this a dict lookup instead
        if contained.client == 'o':
            self.client_info["client"] = "OpenSpades"
        elif contained.client == 'B':
            self.client_info["client"] = "BetterSpades"
            # BetterSpades currently sends the client name in the OS info to
            # deal with old scripts that don't recognize the 'B' indentifier
            match = re.match(r"\ABetterSpades \((.*)\)\Z", contained.os_info)
            if match:
                self.client_info["os_info"] = match.groups()[0]
        elif contained.client == 'a':
            self.client_info["client"] = "ACE"
        else:
            self.client_info["client"] = "Unknown({})".format(contained.client)

        # send extension info to clients that support this packet.
        # skip openspades <= 0.1.3 https://github.com/piqueserver/piqueserver/issues/504
        if contained.client == 'o' and contained.version <= (0, 1, 3):
            log.debug("not sending version request to OpenSpades <= 0.1.3")
        else:
            ext_info = loaders.ProtocolExtensionInfo()
            ext_info.extensions = []
            self.send_contained(ext_info)

    @property
    def client_string(self):
        client = self.client_info.get("client", "Unknown")
        os = self.client_info.get("os_info", "Unknown")
        version = self.client_info.get("version", None)
        version_string = "Unknown" if version is None else ".".join(
            map(str, version))
        if client == os == version_string == "Unknown":
            client = "Probably Voxlap"
            os = "Windows"
            version_string = "0.75"
        return "{} v{} on {}".format(client, version_string, os)

    def check_speedhack(self, x: float, y: float, z: float, distance: None = None) -> bool:
        if not self.speedhack_detect:
            return True
        if distance is None:
            distance = self.rubberband_distance
        position = self.world_object.position
        return (math.fabs(x - position.x) < distance and
                math.fabs(y - position.y) < distance and
                math.fabs(z - position.z) < distance)

    # backwards compatability
    is_valid_position = check_speedhack

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

    def set_location_safe(self, location, center=True):
        x, y, z = location

        if center:
            x -= 0.5
            y -= 0.5
            z += 0.5

        x = int(x)
        y = int(y)
        z = int(z)

        # search for valid locations near the specified point
        for pos in self.protocol.pos_table:
            if self.is_location_free(x + pos[0], y + pos[1], z + pos[2]):
                self.set_location((x + pos[0], y + pos[1], z + pos[2]))
                return True
        return False

    def set_location(self, location=None):
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
        position_data = loaders.PositionData()
        position_data.x = x
        position_data.y = y
        position_data.z = z
        self.send_contained(position_data)

    def refill(self, local: bool = False) -> None:
        self.hp = 100
        self.grenades = 3
        self.blocks = 50
        self.weapon_object.restock()
        if not local:
            restock = loaders.Restock()
            self.send_contained(restock)

    def respawn(self) -> None:
        if self.spawn_call is None:
            self.spawn_call = reactor.callLater(
                self.get_respawn_time(), self.spawn)

    def get_spawn_location(self) -> Tuple[int, int, int]:
        game_mode = self.protocol.game_mode
        if game_mode == TC_MODE:
            try:
                base = random.choice(list(self.team.get_entities()))
                return base.get_spawn_location()
            except IndexError:
                pass
        return self.team.get_random_location(True)

    def get_respawn_time(self) -> float:
        if not self.respawn_time:
            return 0
        if self.protocol.respawn_waves:
            offset = reactor.seconds() % self.respawn_time
        else:
            offset = 0
        return self.respawn_time - offset

    def spawn(self, pos: None = None) -> None:
        self.spawn_call = None
        if self.team is None:
            return
        spectator = self.team.spectator
        create_player = loaders.CreatePlayer()
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
            self.protocol.send_contained(create_player, save=True)
        if not spectator:
            self.on_spawn((x, y, z))

        if not self.client_info:
            handshake_init = loaders.HandShakeInit()
            self.send_contained(handshake_init)

    def take_flag(self):
        if not self.hp:
            return
        flag = self.team.other.flag
        if flag.player is not None:
            return
        if self.on_flag_take() == False:
            return
        flag.player = self
        intel_pickup = loaders.IntelPickup()
        intel_pickup.player_id = self.player_id
        self.protocol.send_contained(intel_pickup, save=True)

    def capture_flag(self):
        other_team = self.team.other
        flag = other_team.flag
        player = flag.player
        if player is not self:
            return
        self.add_score(10)  # 10 points for intel
        self.team.score += 1
        self.on_flag_capture()
        if (self.protocol.max_score not in (0, None) and
                self.team.score >= self.protocol.max_score):
            self.protocol.reset_game(self)
            self.protocol.on_game_end()
        else:
            intel_capture = loaders.IntelCapture()
            intel_capture.player_id = self.player_id
            intel_capture.winning = False
            self.protocol.send_contained(intel_capture, save=True)
            flag = other_team.set_flag()
            flag.update()

    def drop_flag(self) -> None:
        protocol = self.protocol
        game_mode = protocol.game_mode
        if game_mode == CTF_MODE:
            for flag in (protocol.blue_team.flag, protocol.green_team.flag):
                player = flag.player
                if player is not self:
                    continue
                position = self.world_object.position

                # convert to safe coords so the flag can't be dropped out of bounds
                x, y, z = self.protocol.map.get_safe_coords(
                    position.x, position.y, position.z)
                # or inside solid
                z = self.protocol.map.get_z(x, y, z)
                flag.set(x, y, z)

                flag.player = None
                intel_drop = loaders.IntelDrop()
                intel_drop.player_id = self.player_id
                intel_drop.x = flag.x
                intel_drop.y = flag.y
                intel_drop.z = flag.z
                self.protocol.send_contained(intel_drop, save=True)
                self.on_flag_drop()
                break
        elif game_mode == TC_MODE:
            for entity in protocol.entities:
                if self in entity.players:
                    entity.remove_player(self)

    def on_disconnect(self) -> None:
        if self.name is not None:
            self.drop_flag()
            player_left = loaders.PlayerLeft()
            player_left.player_id = self.player_id
            self.protocol.send_contained(player_left, sender=self,
                                         save=True)
            del self.protocol.players[self.player_id]
        if self.player_id is not None:
            self.protocol.player_ids.put_back(self.player_id)
            self.protocol.update_master()
        self.reset()

    def reset(self) -> None:
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

    def hit(self, value, by=None, kill_type=WEAPON_KILL):
        if self.hp is None:
            return
        if by is not None and self.team is by.team:
            friendly_fire = self.protocol.friendly_fire
            friendly_fire_on_grief = self.protocol.friendly_fire_on_grief
            if friendly_fire_on_grief:
                if (kill_type == MELEE_KILL and
                        not self.protocol.spade_teamkills_on_grief):
                    return
                hit_time = self.protocol.friendly_fire_time
                if (self.last_block_destroy is None
                        or reactor.seconds() - self.last_block_destroy >= hit_time):
                    return
            elif not friendly_fire:
                return
        self.set_hp(self.hp - value, by, kill_type=kill_type)

    def set_hp(self, value: Union[int, float], hit_by: Optional['ServerConnection'] = None, kill_type: int = WEAPON_KILL,
               hit_indicator: Optional[Tuple[float, float, float]] = None, grenade: Optional[world.Grenade] = None) -> None:
        value = int(value)
        self.hp = max(0, min(100, value))
        if self.hp <= 0:
            self.kill(hit_by, kill_type, grenade)
            return
        set_hp = loaders.SetHP()
        set_hp.hp = self.hp
        set_hp.not_fall = int(kill_type != FALL_KILL)
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

    def set_weapon(self, weapon: int, local: bool = False, no_kill: bool = False) -> None:
        self.weapon = weapon
        if self.weapon_object is not None:
            self.weapon_object.reset()
        self.weapon_object = WEAPONS[weapon](self._on_reload)
        if not local:
            change_weapon = loaders.ChangeWeapon()
            self.protocol.send_contained(change_weapon, save=True)
            if not no_kill:
                self.kill(kill_type=CLASS_CHANGE_KILL)

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
            self.kill(kill_type=TEAM_CHANGE_KILL)

    def kill(self, by: None = None, kill_type: int = WEAPON_KILL, grenade: None = None) -> None:
        if self.hp is None:
            return
        if self.on_kill(by, kill_type, grenade) is False:
            return
        self.drop_flag()
        self.hp = None
        self.weapon_object.reset()
        kill_action = loaders.KillAction()
        kill_action.kill_type = kill_type
        if by is None:
            kill_action.killer_id = kill_action.player_id = self.player_id
        else:
            kill_action.killer_id = by.player_id
            kill_action.player_id = self.player_id
        if by is not None and by is not self:
            by.add_score(1)
        kill_action.respawn_time = self.get_respawn_time() + 1
        self.protocol.send_contained(kill_action, save=True)
        self.world_object.dead = True
        self.respawn()

    def add_score(self, score):
        self.kills += score

    def _connection_ack(self) -> None:
        self._send_connection_data()
        self.send_map(ProgressiveMapGenerator(self.protocol.map))
        if not self.client_info:
            handshake_init = loaders.HandShakeInit()
            self.send_contained(handshake_init)

    def _send_connection_data(self) -> None:
        saved_loaders = self.saved_loaders = []
        if self.player_id is None:
            for player in self.protocol.players.values():
                if player.name is None:
                    continue
                existing_player = loaders.ExistingPlayer()
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

        state_data = loaders.StateData()
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
            ctf_data = loaders.CTFState()
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

    def grenade_exploded(self, grenade: world.Grenade) -> None:
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
        x = int(math.floor(x))
        y = int(math.floor(y))
        z = int(math.floor(z))
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
                              hit_indicator=position.get(), kill_type=GRENADE_KILL,
                              grenade=grenade)
        if self.on_block_destroy(x, y, z, GRENADE_DESTROY) == False:
            return
        map = self.protocol.map
        for n_x, n_y, n_z in product(range(x - 1, x + 2), range(y - 1, y + 2), range(z - 1, z + 2)):
            count = map.destroy_point(n_x, n_y, n_z)
            if count:
                self.total_blocks_removed += count
                self.on_block_removed(n_x, n_y, n_z)
        block_action = loaders.BlockAction()
        block_action.x = x
        block_action.y = y
        block_action.z = z
        block_action.value = GRENADE_DESTROY
        block_action.player_id = self.player_id
        self.protocol.send_contained(block_action, save=True)
        self.protocol.update_entities()

    def _on_fall(self, damage: int) -> None:
        if not self.hp:
            return
        returned = self.on_fall(damage)
        if returned is False:
            return
        elif returned is not None:
            damage = returned
        self.set_hp(self.hp - damage, kill_type=FALL_KILL)

    def _on_reload(self):
        weapon_reload = loaders.WeaponReload()
        weapon_reload.player_id = self.player_id
        weapon_reload.clip_ammo = self.weapon_object.current_ammo
        weapon_reload.reserve_ammo = self.weapon_object.current_stock
        self.send_contained(weapon_reload)

    def send_map(self, data: Optional[ProgressiveMapGenerator] = None) -> None:
        if data is not None:
            self.map_data = data
            map_start = loaders.MapStart()
            map_start.size = data.get_size()
            self.send_contained(map_start)
        elif self.map_data is None:
            return

        if not self.map_data.data_left():
            log.debug("done sending map data to {player}", player=self)
            self.map_data = None
            for data in self.saved_loaders:
                packet = enet.Packet(bytes(data), enet.PACKET_FLAG_RELIABLE)
                self.peer.send(0, packet)
            self.saved_loaders = None
            self.on_join()
            return
        for _ in range(10):
            if not self.map_data.data_left():
                break
            map_data = loaders.MapChunk()
            map_data.data = self.map_data.read(8192)
            self.send_contained(map_data)

    def continue_map_transfer(self) -> None:
        self.send_map()

    def send_data(self, data):
        self.protocol.transport.write(data, self.address)

    def send_chat(self, value: str, global_message: bool = False) -> None:
        if self.deaf:
            return
        chat_message = loaders.ChatMessage()
        if not global_message:
            chat_message.chat_type = CHAT_SYSTEM
            prefix = ''
        else:
            chat_message.chat_type = CHAT_TEAM
            # 34 is guaranteed to be out of range!
            chat_message.player_id = 35
            prefix = self.protocol.server_prefix + ' '

        lines = textwrap.wrap(value, MAX_CHAT_SIZE - len(prefix) - 1)

        for line in lines:
            chat_message.value = '{}{}'.format(prefix, line)
            self.send_contained(chat_message)

    def send_chat_warning(self, message):
        """
        Send a warning message. This gets displayed as a yellow popup
        with sound for OpenSpades clients
        """
        self.send_chat("%% " + str(message))

    def send_chat_notice(self, message):
        """
        Send a notice. This gets displayed as a popup for OpenSpades
        clients
        """
        self.send_chat("N% " + str(message))

    def send_chat_error(self, message):
        """
        Send a error message. This gets displayed as a red popup with
        sound for OpenSpades clients
        """
        self.send_chat("!% " + str(message))

    def send_chat_status(self, message):
        """
        Send a status message. This gets displayed in the center of the
        screen for OpenSpades clients
        """
        self.send_chat("C% " + str(message))

    # events/hooks

    def on_join(self):
        pass

    def on_login(self, name):
        pass

    def on_spawn(self, pos: Tuple[float, float, float]) -> None:
        pass

    def on_spawn_location(self, pos: Tuple[float, float, float]) -> None:
        pass

    def on_chat(self, value, global_message):
        pass

    def on_chat_sent(self, value: str, global_message: bool) -> None:
        pass

    def on_command(self, command, parameters):
        pass

    def on_hit(self, hit_amount, hit_player, kill_type, grenade):
        pass

    def on_kill(self, killer, kill_type, grenade):
        pass

    def on_team_join(self, team):
        pass

    def on_team_changed(self, old_team: Team) -> None:
        pass

    def on_tool_set_attempt(self, tool: int) -> None:
        pass

    def on_tool_changed(self, tool: int) -> None:
        pass

    def on_grenade(self, time_left):
        pass

    def on_grenade_thrown(self, grenade: world.Grenade) -> None:
        pass

    def on_block_build_attempt(self, x, y, z):
        pass

    def on_block_build(self, x, y, z):
        pass

    def on_line_build_start(self):
        """called when the player has pressed the mouse button to start
        line-building"""

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

    def on_color_set_attempt(self, color: Tuple[int, int, int]) -> None:
        pass

    def on_color_set(self, color: Tuple[int, int, int]) -> None:
        pass

    def on_flag_take(self):
        pass

    def on_flag_capture(self):
        pass

    def on_flag_drop(self):
        pass

    def on_hack_attempt(self, reason):
        pass

    def on_position_update(self) -> None:
        pass

    def on_weapon_set(self, value):
        pass

    def on_fall(self, damage):
        pass

    def on_reset(self):
        pass

    def on_orientation_update(self, x: float, y: float, z: float) -> None:
        pass

    def on_shoot_set(self, fire: int) -> None:
        pass

    def on_secondary_fire_set(self, secondary):
        pass

    def on_walk_update(self, up: bool, down: bool, left: bool, right: bool) -> None:
        pass

    def on_animation_update(self, jump, crouch, sneak, sprint):
        pass

    def __repr__(self):
        return "<{} player_id: {!r}, name: {!r}, address: {!r} at 0x{:x}>".format(
            self.__class__.__name__, self.player_id, self.name, self.address,
            id(self)
        )
