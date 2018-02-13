"""
push.py last modified 2013-10-30 17:39:12
Contributors: danhezee, StackOverflow, izzy, Danke, noway421, IAmYourFriend

The concept:
    Each team spawns at a set location with the enemy intel.
    They must "push" the intel towards their control point, which is also at a
    set location.

How to setup new maps:
    Spawn and CP locations must be configured via extensions in the map's
    map_name.txt metadata. Example:

>>> extensions = {
...     'push': True,
...     'push_spawn_range' : 5,
...     'push_blue_spawn' : (91, 276, 59),
...     'push_blue_cp' : (91, 276, 59),
...     'push_green_spawn' : (78, 86, 59),
...     'push_green_cp' : (78, 86, 59),
...     'water_damage' : 100
... }

Additional, but optional extensions, to mark each teams build area and prevent
the enemy from building there (and thereby helping the enemy). The build area
is defined by x and y of upper left corner, followed by x and y of bottom right
corner on the map. Example::

    'push_blue_build_area' : (172, 140, 216, 402),
    'push_green_build_area' : (266, 145, 309, 408),

ToDo:
    Block check by global array (For example, blockdata.py), not block color.
    One time violet block spawns. Wtf!
    Serverside player blocks stack. Cannot control filling stack on clientside.
"""


from six.moves import range
from pyspades.constants import *
from pyspades.common import make_color
from pyspades.contained import SetColor, BlockAction
from piqueserver.commands import command, admin
from twisted.internet.task import LoopingCall
from random import randint

import colorsys


def byte_rgb_to_hls(rgb):
    hls = colorsys.rgb_to_hls(*tuple(c / 255.0 for c in rgb))
    return tuple(int(round(c * 255)) for c in hls)


def byte_hls_to_rgb(hls):
    rgb = colorsys.hls_to_rgb(*tuple(c / 255.0 for c in hls))
    return tuple(int(round(c * 255)) for c in rgb)


def byte_middle_range(byte):
    half = 50 / 2.0  # half of (byte/5.1)
    min = byte - half
    max = byte + half
    if min < 0:
        min = 0
        max = half
    elif max > 255:
        min = 255 - half
        max = 255
    return int(round(min)), int(round(max))


# If ALWAYS_ENABLED is False, then the 'push' key must be set to True in
# the 'extensions' dictionary in the map's map_name.txt metadata
ALWAYS_ENABLED = True
CANT_DESTROY = "You can't destroy your team's blocks. Attack the enemy!"
NO_BLOCKS = "You out of blocks! Kill yourself or reach base to refill."
BUILDING_AT_CP = "You can't build near your command post!"
BUILDING_AT_ENEMY_AREA = "Don't build for your enemy!"
# team is associated intel team


def reset_intel(protocol, team):
    if team is protocol.green_team and protocol.blue_team.spawn is not None:
        z = protocol.map.get_z(*protocol.blue_team.spawn)
        pos = (protocol.blue_team.spawn[0],
               protocol.blue_team.spawn[1],
               z)

    if team is protocol.blue_team and protocol.green_team.spawn is not None:
        z = protocol.map.get_z(*protocol.green_team.spawn)
        pos = (protocol.green_team.spawn[0],
               protocol.green_team.spawn[1],
               z)

    team.flag.set(*pos)  # If spawn not set, it would throw error.
    team.flag.update()
    protocol.send_chat("The %s intel has been reset." % team.name)


@command(admin_only=True)
def resetblueintel(connection):
    reset_intel(connection.protocol, connection.protocol.blue_team)


@command(admin_only=True)
def resetgreenintel(connection):
    reset_intel(connection.protocol, connection.protocol.green_team)


def get_entity_location(self, entity_id):
    if entity_id == BLUE_BASE:
        return self.protocol.blue_team.cp
    elif entity_id == GREEN_BASE:
        return self.protocol.green_team.cp

    # this next part might seem counter intuitive but you need the blue intel
    # to spawn near the greens and vice versa
    elif entity_id == BLUE_FLAG:
        return self.protocol.green_team.spawn
    elif entity_id == GREEN_FLAG:
        return self.protocol.blue_team.spawn


def get_spawn_location(connection):
    # distance from spawn center to randomly spawn in
    spawn_range = connection.protocol.spawn_range

    if connection.team.spawn is not None:
        xb = connection.team.spawn[0]
        yb = connection.team.spawn[1]
        xb += randint(-spawn_range, spawn_range)
        yb += randint(-spawn_range, spawn_range)
        return (xb, yb, connection.protocol.map.get_z(xb, yb))


def apply_script(protocol, connection, config):
    class PushConnection(connection):

        def invalid_build_position_check(
                self, x, y, check_area, error_message):
            # check_area is made of x-pos, y-pos of upper left corner,
            # and x-pos, y-pos of opposite corner (bottom right)
            if (x >= check_area[0] and y >= check_area[1] and
                    x <= check_area[2] and y <= check_area[3]):
                self.send_chat(error_message)
                return True
            else:
                return False

        def invalid_build_position(self, x, y, z):
            # prevent teams from building near their cp
            cp_block_range = 8
            if self.team is self.protocol.blue_team:
                blue_cp_area = (self.protocol.blue_team.cp[0] - cp_block_range,
                                self.protocol.blue_team.cp[1] - cp_block_range,
                                self.protocol.blue_team.cp[0] + cp_block_range,
                                self.protocol.blue_team.cp[1] + cp_block_range)
                invalid_pos = self.invalid_build_position_check(
                    x, y, blue_cp_area, BUILDING_AT_CP)
                if invalid_pos is True:
                    return True
            if self.team is self.protocol.green_team:
                green_cp_area = (
                    self.protocol.green_team.cp[0] - cp_block_range,
                    self.protocol.green_team.cp[1] - cp_block_range,
                    self.protocol.green_team.cp[0] + cp_block_range,
                    self.protocol.green_team.cp[1] + cp_block_range)
                invalid_pos = self.invalid_build_position_check(
                    x, y, green_cp_area, BUILDING_AT_CP)
                if invalid_pos is True:
                    return True
            # prevent teams from building in enemy build area
            if (self.team is self.protocol.blue_team and
                    self.protocol.blue_team.build_area is not None):
                invalid_pos = self.invalid_build_position_check(
                    x, y,
                    self.protocol.green_team.build_area,
                    BUILDING_AT_ENEMY_AREA)
                if invalid_pos is True:
                    return True
            if (self.team is self.protocol.green_team and
                    self.protocol.green_team.build_area is not None):
                invalid_pos = self.invalid_build_position_check(
                    x, y, self.protocol.blue_team.build_area, BUILDING_AT_ENEMY_AREA)
                if invalid_pos is True:
                    return True

            return False

        def on_login(self, name):
            self.mylastblocks = [
                (-4, -1, -14),
                (-11, -5, -9),
                (-19, -20, -8)]
            return connection.on_login(self, name)

        def random_color(self):
            (h, l, s) = self.team.hls
            l = randint(self.team.light_range[0], self.team.light_range[1])
            color = byte_hls_to_rgb((h, l, s))

            self.color = color
            set_color = SetColor()
            set_color.player_id = self.player_id
            set_color.value = make_color(*color)
            self.send_contained(set_color)
            self.protocol.send_contained(set_color, save=True)

        def build_block(self, x, y, z, looped=False):
            if ((x < 0 or x > 511 or
                 y < 0 or y > 511 or
                 z < 1 or z > 61)
                    is False):
                self.protocol.map.set_point(x, y, z, self.color)
                block_action = BlockAction()
                block_action.x = x
                block_action.y = y
                block_action.z = z
                block_action.value = BUILD_BLOCK
                block_action.player_id = self.player_id
                self.protocol.send_contained(block_action, save=True)

        def on_line_build_attempt(self, points):
            can_build = connection.on_line_build_attempt(self, points)
            if can_build is False:
                return False

            if self.blocks < len(points):
                self.send_chat(NO_BLOCKS)
                return False

            for point in points:
                if self.invalid_build_position(*point):
                    return False

            spawn = self.team.spawn
            spawn_range = self.protocol.spawn_range

            for point in points:
                x, y, z = point[0], point[1], point[2]
                self.random_color()

            return can_build

        def on_block_build_attempt(self, x, y, z):
            can_build = connection.on_block_build_attempt(self, x, y, z)
            if can_build is False:
                return False

            if self.blocks < 0:
                self.send_chat(NO_BLOCKS)
                return False

            if self.invalid_build_position(x, y, z):
                return False

            self.mylastblocks.pop(0)
            self.mylastblocks.append((x, y, z))
            self.random_color()
            return can_build

        def on_block_destroy(self, x, y, z, value):
            if not (self.admin or
                    self.god or
                    self.user_types.moderator or
                    self.user_types.guard or
                    self.user_types.trusted):
                if value == DESTROY_BLOCK:
                    blocks = ((x, y, z),)
                elif value == SPADE_DESTROY:
                    blocks = ((x, y, z), (x, y, z + 1), (x, y, z - 1))
                elif value == GRENADE_DESTROY:
                    blocks = []
                    for nade_x in range(x - 1, x + 2):
                        for nade_y in range(y - 1, y + 2):
                            for nade_z in range(z - 1, z + 2):
                                blocks.append((nade_x, nade_y, nade_z))

                def is_in_last(block): return any(last == block
                                                  for last in self.mylastblocks)

                for block in blocks:
                    if is_in_last(block):
                        continue

                    block_info = self.protocol.map.get_point(*block)

                    if block_info[0] is True:
                        block_hls = byte_rgb_to_hls(block_info[1])
                        if self.team is self.protocol.blue_team:
                            team_hls = self.protocol.blue_team.hls
                            # if hue and saturation match
                            if (block_hls[0] == team_hls[0] and
                                    block_hls[2] == team_hls[2]):
                                self.send_chat(CANT_DESTROY)
                                return False
                        elif self.team is self.protocol.green_team:
                            team_hls = self.protocol.green_team.hls
                            if (block_hls[0] == team_hls[0] and
                                    block_hls[2] == team_hls[2]):
                                self.send_chat(CANT_DESTROY)
                                return False

                for block in blocks:
                    if is_in_last(block):
                        self.mylastblocks.remove(block)
                        self.mylastblocks.append((-1, -1, -1))

            return connection.on_block_destroy(self, x, y, z, value)

    class PushProtocol(protocol):
        game_mode = CTF_MODE
        push = False
        spawn_range = 5
        check_loop = None
        reset_intel_after_seconds = 300
        reset_intel_blue_timer = 0
        reset_intel_green_timer = 0

        def __init__(self, *arg, **kw):
            protocol.__init__(self, *arg, **kw)
            self.blue_team.hls = byte_rgb_to_hls(self.blue_team.color)
            self.blue_team.light_range = byte_middle_range(
                self.blue_team.hls[1])

            self.green_team.hls = byte_rgb_to_hls(self.green_team.color)
            self.green_team.light_range = byte_middle_range(
                self.green_team.hls[1])

        def check_intel_locations(self):
            if self.blue_team.flag is not None:
                if self.blue_team.flag.get()[2] >= 63:
                    self.reset_intel_blue_timer = 0
                    reset_intel(self, self.blue_team)
                elif self.blue_team.flag.player is None:
                    self.reset_intel_blue_timer += 1
                    if self.reset_intel_blue_timer >= self.reset_intel_after_seconds:
                        self.reset_intel_blue_timer = 0
                        reset_intel(self, self.blue_team)
                else:
                    self.reset_intel_blue_timer = 0

            if self.green_team.flag is not None:
                if self.green_team.flag.get()[2] >= 63:
                    self.reset_intel_green_timer = 0
                    reset_intel(self, self.green_team)
                elif self.green_team.flag.player is None:
                    self.reset_intel_green_timer += 1
                    if self.reset_intel_green_timer >= self.reset_intel_after_seconds:
                        self.reset_intel_green_timer = 0
                        reset_intel(self, self.green_team)
                else:
                    self.reset_intel_green_timer = 0

        def on_map_change(self, map):
            extensions = self.map_info.extensions
            if ALWAYS_ENABLED:
                self.push = True
            else:
                self.push = extensions.get('push', False)

            if self.push:
                # distance from spawn center to randomly spawn in
                self.spawn_range = extensions.get('push_spawn_range')

                self.blue_team.spawn = extensions.get('push_blue_spawn')
                self.blue_team.cp = extensions.get('push_blue_cp')
                self.blue_team.build_area = extensions.get(
                    'push_blue_build_area')

                self.green_team.spawn = extensions.get('push_green_spawn')
                self.green_team.cp = extensions.get('push_green_cp')
                self.green_team.build_area = extensions.get(
                    'push_green_build_area')

                self.map_info.get_entity_location = get_entity_location
                self.map_info.get_spawn_location = get_spawn_location

                if self.check_loop is not None:
                    self.check_loop.stop()
                self.reset_intel_blue_timer = 0
                self.reset_intel_green_timer = 0
                self.check_loop = LoopingCall(self.check_intel_locations)
                self.check_loop.start(1)

            return protocol.on_map_change(self, map)

    return PushProtocol, PushConnection
