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

from __future__ import print_function

import random
from itertools import product
import enet

from pyspades.protocol import BaseProtocol
from pyspades.constants import (
    CTF_MODE, TC_MODE, GAME_VERSION, MIN_TERRITORY_COUNT, MAX_TERRITORY_COUNT,
    UPDATE_FREQUENCY, UPDATE_FPS, NETWORK_FPS)
from pyspades.types import MultikeyDict, IDPool
from pyspades.master import get_master_connection
#from pyspades.debug import *
from pyspades.team import Team
from pyspades.entities import Territory
# importing tc_data is a quick hack since this file writes into it
from pyspades.player import ServerConnection, tc_data
from pyspades import world
from pyspades.bytes import ByteWriter
from pyspades import contained as loaders
from pyspades.common import make_color
from pyspades.mapgenerator import ProgressiveMapGenerator

try:
    range = xrange # pylint: disable=redefined-builtin
except NameError:
    pass

fog_color = loaders.FogColor()
world_update = loaders.WorldUpdate()
intel_capture = loaders.IntelCapture()
territory_capture = loaders.TerritoryCapture()

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
    server_prefix = '[*] '
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
        self.team_spectator = self.team_class(-1, self.spectator_name,
                                              (0, 0, 0), True, self)
        self.team_1 = self.team_class(0, self.team1_name, self.team1_color,
                                      False, self)
        self.team_2 = self.team_class(1, self.team2_name, self.team2_color,
                                      False, self)
        self.teams = {
            -1: self.spectator_team,
            0: self.team_1,
            1: self.team_2
        }
        self.team_1.other = self.team_2
        self.team_2.other = self.team_1
        self.world = world.World()
        self.set_master()

        # safe position LUT
        #
        # Generates a LUT to check for safe positions. The slighly weird
        # sorting is used to sort by increasing distance so the nearest spots
        # get chosen first
        # product(repeat=3) is the equivalent of 3 nested for loops
        self.pos_table = list(product(range(-5, 6), repeat=3))

        self.pos_table.sort(key=lambda vec: abs(vec[0] * 1.03) +
                            abs(vec[1] * 1.02) +
                            abs(vec[2] * 1.01))

    @property
    def blue_team(self):
        """alias to team_1 for backwards-compatibility"""
        return self.team_1

    @property
    def green_team(self):
        """alias to team_2 for backwards-compatibility"""
        return self.team_2

    @property
    def spectator_team(self):
        """alias to team_spectator for backwards-compatibility"""
        return self.team_spectator

    def send_contained(self, contained, unsequenced=False, sender=None,
                       team=None, save=False, rule=None):
        if unsequenced:
            flags = enet.PACKET_FLAG_UNSEQUENCED
        else:
            flags = enet.PACKET_FLAG_RELIABLE
        writer = ByteWriter()
        contained.write(writer)
        data = bytes(writer)
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
        territory_count = int((land_count / (512.0 * 512.0)) * (
            MAX_TERRITORY_COUNT - MIN_TERRITORY_COUNT) + MIN_TERRITORY_COUNT)
        j = 512.0 / territory_count
        for i in range(territory_count):
            x1 = i * j
            y1 = 512 / 4
            x2 = (i + 1) * j
            y2 = y1 * 3
            flag = Territory(i, self, *self.get_random_location(
                zone=(x1, y1, x2, y2)))
            if i < territory_count / 2:
                team = self.team_1
            elif i > (territory_count - 1) / 2:
                team = self.team_2
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
        for i in range(32):
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
        self.send_contained(world_update, unsequenced=True)

    def set_map(self, map_obj):
        self.map = map_obj
        self.world.map = map_obj
        self.on_map_change(map_obj)
        self.team_1.initialize()
        self.team_2.initialize()
        if self.game_mode == TC_MODE:
            self.reset_tc()
        self.players = MultikeyDict()
        if self.connections:
            data = ProgressiveMapGenerator(self.map, parent=True)
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

    def reset_game(self, player=None, territory=None):
        """reset the score of the game

        player is the player which should be awarded the necessary captures to
        end the game
        """
        self.team_1.initialize()
        self.team_2.initialize()
        if self.game_mode == CTF_MODE:
            if player is None:
                player = list(self.players.values())[0]
            intel_capture.player_id = player.player_id
            intel_capture.winning = True
            self.send_contained(intel_capture, save=True)
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
        '''
        Sanitizes `name` and modifies it so that it doesn't collide with other names connected to the server.

        Returns the fixed name.
        '''
        name = name.replace('%', '')
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

    def get_random_location(self, force_land=True, zone=(0, 0, 512, 512)):
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

    def master_disconnected(self, client=None):
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
        map_obj = self.map
        for entity in self.entities:
            moved = False
            if map_obj.get_solid(entity.x, entity.y, entity.z - 1):
                moved = True
                entity.z -= 1
                # while solid in block above (ie. in the space in which the
                # entity is sitting), move entity up)
                while map_obj.get_solid(entity.x, entity.y, entity.z - 1):
                    entity.z -= 1
            else:
                # get_solid can return None, so a more specific check is used
                while map_obj.get_solid(entity.x, entity.y, entity.z) is False:
                    moved = True
                    entity.z += 1
            if moved or self.on_update_entity(entity):
                entity.update()

    def broadcast_chat(self, message, global_message=None, sender=None,
                       team=None):
        for player in self.players.values():
            if player is sender:
                continue
            if player.deaf:
                continue
            if team is not None and player.team is not team:
                continue
            player.send_chat(message, global_message)

    # backwards compatability
    send_chat = broadcast_chat

    def broadcast_chat_warning(self, message, team=None):
        """
        Send a warning message. This gets displayed
        as a yellow popup with sound for OpenSpades
        clients
        """
        self.send_chat(self, "%% " + str(message), team=team)

    def broadcast_chat_notice(self, message, team=None):
        """
        Send a warning message. This gets displayed
        as a popup for OpenSpades
        clients
        """
        self.send_chat(self, "N% " + str(message), team=team)

    def broadcast_chat_error(self, message, team=None):
        """
        Send a warning message. This gets displayed
        as a red popup with sound for OpenSpades
        clients
        """
        self.send_chat(self, "!% " + str(message), team=team)

    def broadcast_chat_status(self, message, team=None):
        """
        Send a warning message. This gets displayed
        as a red popup with sound for OpenSpades
        clients
        """
        self.send_chat(self, "C% " + str(message), team=team)


    def set_fog_color(self, color):
        self.fog_color = color
        fog_color.color = make_color(*color)
        self.send_contained(fog_color, save=True)

    def get_fog_color(self):
        return self.fog_color

    # events

    def on_cp_capture(self, cp):
        pass

    def on_game_end(self):
        pass

    def on_world_update(self):
        pass

    def on_map_change(self, map_):
        pass

    def on_base_spawn(self, x, y, z, base, entity_id):
        pass

    def on_flag_spawn(self, x, y, z, flag, entity_id):
        pass

    def on_update_entity(self, entity):
        pass
