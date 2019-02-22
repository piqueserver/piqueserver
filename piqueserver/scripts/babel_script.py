"""
babel_script.py last modified 2014-04-04 13:55:07
Original script by Yourself
Anti grief by izzy
Return intel dropped from platform bug fix by a_girl

Release thread:
http://www.buildandshoot.com/viewtopic.php?t=2586

How to install and configure:

1) Save babel_script.py to 'scripts' folder:
http://aloha.pk/files/aos/pyspades/feature_server/scripts/babel_script.py
2) Save babel.py to 'scripts' folder:
http://aloha.pk/files/aos/pyspades/feature_server/scripts/babel.py
3) Set game_mode to "babel" in config.txt
4) Add "babel_script" to scripts list in config.txt
5) Set cap_limit to "10" in config.txt
"""

from random import randint
from pyspades.constants import (BLUE_BASE, GREEN_BASE, BLUE_FLAG, GREEN_FLAG,
                                SPADE_TOOL, GRENADE_TOOL, WEAPON_TOOL)
from twisted.internet import reactor

# If ALWAYS_ENABLED is False, then babel can be enabled by setting 'babel': True
# in the map metadat extensions dictionary.
ALWAYS_ENABLED = True

PLATFORM_WIDTH = 100
PLATFORM_HEIGHT = 32
PLATFORM_COLOR = (0, 255, 255, 255)
BLUE_BASE_COORDS = (256 - 138, 256)
GREEN_BASE_COORDS = (256 + 138, 256)
SPAWN_SIZE = 40

# Don't touch this stuff
PLATFORM_WIDTH //= 2
PLATFORM_HEIGHT //= 2
SPAWN_SIZE //= 2


def get_entity_location(self, entity_id):
    if entity_id == BLUE_BASE:
        return BLUE_BASE_COORDS + (self.protocol.map.get_z(*BLUE_BASE_COORDS),)
    elif entity_id == GREEN_BASE:
        return GREEN_BASE_COORDS + \
            (self.protocol.map.get_z(*GREEN_BASE_COORDS),)
    elif entity_id == BLUE_FLAG:
        return (256 - PLATFORM_WIDTH + 1, 256, 0)
    elif entity_id == GREEN_FLAG:
        return (256 + PLATFORM_WIDTH - 1, 256, 0)


def get_spawn_location(connection):
    xb = connection.team.base.x
    yb = connection.team.base.y
    xb += randint(-SPAWN_SIZE, SPAWN_SIZE)
    yb += randint(-SPAWN_SIZE, SPAWN_SIZE)
    return (xb, yb, connection.protocol.map.get_z(xb, yb))


def coord_on_platform(x, y, z):
    if z <= 2:
        if (256 - PLATFORM_WIDTH <= x <= 256 + PLATFORM_WIDTH and
                256 - PLATFORM_HEIGHT <= y <= 256 + PLATFORM_HEIGHT):
            return True
    if z == 1:
        if (256 - PLATFORM_WIDTH - 1 <= x <= 256 + PLATFORM_WIDTH + 1
            and 256 - PLATFORM_HEIGHT - 1 <= y <= 256 + PLATFORM_HEIGHT + 1):
            return True
    return False

def apply_script(protocol, connection, config):
    allowed_intel_hold_time = config.get('allowed_intel_hold_time', 150)

    class TowerOfBabelConnection(connection):
        def get_protected_area(self, team):
            """returns minx, maxx, miny, maxy"""
            if team is self.protocol.blue_team:
                return 301, 384, 240, 272
            else:
                return 128, 211, 240, 272

        def invalid_build_position(self, x, y, z):
            position = self.world_object.position

            if not self.god and self.protocol.babel:
                if coord_on_platform(x, y, z):
                    connection.on_block_build_attempt(self, x, y, z)
                    return True
            # prevent enemies from building in protected areas

            minx, maxx, miny, maxy = self.get_protected_area(self.team)
            if minx <= position.x <= maxx and miny <= position.y <= maxy:
                self.send_chat('You can\'t build near the enemy\'s tower!')
                return True
            return False

        def on_block_build_attempt(self, x, y, z):
            if self.invalid_build_position(x, y, z):
                return False
            return connection.on_block_build_attempt(self, x, y, z)

        def on_line_build_attempt(self, points):
            for point in points:
                if self.invalid_build_position(*point):
                    return False
            return connection.on_line_build_attempt(self, points)

        def is_trusted_for_block_destruction(self):
            return self.admin or self.user_types.moderator or self.user_types.guard or self.user_types.trusted

        # anti team destruction
        def on_block_destroy(self, x, y, z, mode):
            minx, maxx, miny, maxy = self.get_protected_area(self.team.other)

            position = self.world_object.position

            if not self.is_trusted_for_block_destruction() and self.tool is SPADE_TOOL:
                if minx <= position.x <= maxx and miny <= position.y <= maxy:
                    self.send_chat('You can\'t destroy your team\'s blocks in this area. Attack the enemy\'s tower!')
                    return False

            if self.team is self.protocol.blue_team:
                can_shoot_blocks = position.x <= 288
            else:
                can_shoot_blocks = position.x >= 224

            if can_shoot_blocks:
                if self.tool is WEAPON_TOOL:
                    self.send_chat('You must be closer to the enemy\'s base to shoot blocks!')
                else:
                    self.send_chat('You must be closer to the enemy\'s base to grenade blocks!')
                return False
            return connection.on_block_destroy(self, x, y, z, mode)

        auto_kill_intel_hog_call = None

        # kill intel carrier if held too long
        def auto_kill_intel_hog(self):
            self.auto_kill_intel_hog_call = None
            self.kill()
            self.protocol.send_chat(
                'God punished %s for holding the intel too long' %
                (self.name))

        def restore_default_fog_color(self):
            self.protocol.set_fog_color(
                getattr(self.protocol.map_info.info, 'fog', (128, 232, 255)))

        def on_flag_take(self):
            if self.auto_kill_intel_hog_call is not None:
                self.auto_kill_intel_hog_call.cancel()
                self.auto_kill_intel_hog_call = None
            self.auto_kill_intel_hog_call = reactor.callLater(
                allowed_intel_hold_time, self.auto_kill_intel_hog)
            # flash team color in sky
            if self.team is self.protocol.blue_team:
                self.protocol.set_fog_color(
                    getattr(self.protocol.map_info.info, 'fog', (0, 0, 255)))
            if self.team is self.protocol.green_team:
                self.protocol.set_fog_color(
                    getattr(self.protocol.map_info.info, 'fog', (0, 255, 0)))
            reactor.callLater(0.25, self.restore_default_fog_color)
            return connection.on_flag_take(self)

        # return intel to platform if dropped
        def on_flag_drop(self):
            x, y, z = self.world_object.position.x, self.world_object.position.y, self.world_object.position.z
            if self.auto_kill_intel_hog_call is not None:
                self.auto_kill_intel_hog_call.cancel()
                self.auto_kill_intel_hog_call = None
            if z >= 0:
                self.reset_flag()
            elif (x >= (256 + PLATFORM_WIDTH)) or (x < (256 - PLATFORM_WIDTH)):
                self.reset_flag()
            elif (y >= (256 + PLATFORM_HEIGHT)) or (y < (256 - PLATFORM_HEIGHT)):
                self.reset_flag()
            self.protocol.set_fog_color(
                getattr(self.protocol.map_info.info, 'fog', (255, 0, 0)))
            reactor.callLater(0.25, self.restore_default_fog_color)
            return connection.on_flag_drop(self)

        def reset_flag(self):
            self.protocol.onectf_reset_flags()
            self.protocol.send_chat('The intel has returned to the heavens')

        def on_flag_capture(self):
            if self.auto_kill_intel_hog_call is not None:
                self.auto_kill_intel_hog_call.cancel()
                self.auto_kill_intel_hog_call = None
            return connection.on_flag_capture(self)

        def on_reset(self):
            if self.auto_kill_intel_hog_call is not None:
                self.auto_kill_intel_hog_call.cancel()
                self.auto_kill_intel_hog_call = None
            return connection.on_reset(self)

    class TowerOfBabelProtocol(protocol):
        babel = False

        def on_map_change(self, map):
            extensions = self.map_info.extensions
            if ALWAYS_ENABLED:
                self.babel = True
            else:
                if "babel" in extensions:
                    self.babel = extensions['babel']
                else:
                    self.babel = False
            if self.babel:
                self.map_info.cap_limit = 1
                self.map_info.get_entity_location = get_entity_location
                self.map_info.get_spawn_location = get_spawn_location
                for x in range(256 - PLATFORM_WIDTH, 256 + PLATFORM_WIDTH):
                    for y in range(
                            256 - PLATFORM_HEIGHT,
                            256 + PLATFORM_HEIGHT):
                        map.set_point(x, y, 1, PLATFORM_COLOR)
            return protocol.on_map_change(self, map)

        def is_indestructable(self, x, y, z):
            if self.babel:
                if coord_on_platform(x, y, z):
                    protocol.is_indestructable(self, x, y, z)
                    return True
            return protocol.is_indestructable(self, x, y, z)

    return TowerOfBabelProtocol, TowerOfBabelConnection
