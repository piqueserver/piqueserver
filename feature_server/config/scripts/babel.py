# Tower of Babel created by Yourself, modified by izzy
#    how to install:
# set game_mode to ctf in config.txt
# add babel to script list in config.txt
# add to map .txt files: extensions = { 'babel' : True }
#    additional suggestions:
# add onectf to script list in config.txt http://pyspades.googlecode.com/hg/contrib/scripts/onectf.py
# set cap_limit to 10 in config.txt

from pyspades.constants import *
from random import randint

# If ALWAYS_ENABLED is False, then babel can be enabled by setting 'babel': True
# in the map metadat extensions dictionary.
ALWAYS_ENABLED = True

PLATFORM_WIDTH = 100
PLATFORM_HEIGHT = 32
PLATFORM_COLOR = (255, 255, 255, 255)
BLUE_BASE_COORDS = (256-138, 256)
GREEN_BASE_COORDS = (256+138, 256)
SPAWN_SIZE = 40


# Don't touch this stuff
PLATFORM_WIDTH /= 2
PLATFORM_HEIGHT /= 2
SPAWN_SIZE /= 2

def get_entity_location(self, entity_id):
    if entity_id == BLUE_BASE:
        return BLUE_BASE_COORDS + (self.protocol.map.get_z(*BLUE_BASE_COORDS),)
    elif entity_id == GREEN_BASE:
        return GREEN_BASE_COORDS + (self.protocol.map.get_z(*GREEN_BASE_COORDS),)
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
        if x >= (256 - PLATFORM_WIDTH) and x <= (256 + PLATFORM_WIDTH) and y >= (256 - PLATFORM_HEIGHT) and y <= (256 + PLATFORM_HEIGHT):
            return True
    if z == 1:
        if x >= (256 - PLATFORM_WIDTH - 1) and x <= (256 + PLATFORM_WIDTH + 1) \
           and y >= (256 - PLATFORM_HEIGHT - 1) and y <= (256 + PLATFORM_HEIGHT + 1):
            return True
    return False

def apply_script(protocol, connection, config):
    class BabelProtocol(protocol):
        babel = False
        def on_map_change(self, map):
            extensions = self.map_info.extensions
            if ALWAYS_ENABLED:
                self.babel = True
            else:
                if extensions.has_key('babel'):
                    self.babel = extensions['babel']
                else:
                    self.babel = False
            if self.babel:
                self.map_info.cap_limit = 1
                self.map_info.get_entity_location = get_entity_location
                self.map_info.get_spawn_location = get_spawn_location
                for x in xrange(256 - PLATFORM_WIDTH, 256 + PLATFORM_WIDTH):
                    for y in xrange(256 - PLATFORM_HEIGHT, 256 + PLATFORM_HEIGHT):
                        map.set_point(x, y, 1, PLATFORM_COLOR)
            return protocol.on_map_change(self, map)

        def is_indestructable(self, x, y, z):
            if self.babel:
                if coord_on_platform(x, y, z):
                    protocol.is_indestructable(self, x, y, z)
                    return True
            return protocol.is_indestructable(self, x, y, z)

    class BabelConnection(connection):
        def invalid_build_position(self, x, y, z):
            if not self.god and self.protocol.babel:
                if coord_on_platform(x, y, z):
                    connection.on_block_build_attempt(self, x, y, z)
                    return True
            # prevent enemies from building in protected areas
            if self.team is self.protocol.blue_team:
                if self.world_object.position.x >= 301 and self.world_object.position.x <= 384 \
                    and self.world_object.position.y >= 240 and self.world_object.position.y <= 272:
                        self.send_chat('You can\'t build near the enemy\'s tower!')
                        return True
            if self.team is self.protocol.green_team:
                if self.world_object.position.x >= 128 and self.world_object.position.x <= 211 \
                    and self.world_object.position.y >= 240 and self.world_object.position.y <= 272:
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

        # anti team destruction
        def on_block_destroy(self, x, y, z, mode):
            if self.team is self.protocol.blue_team:
                if self.tool is SPADE_TOOL and self.world_object.position.x >= 128 and self.world_object.position.x <= 211 \
                    and self.world_object.position.y >= 240 and self.world_object.position.y <= 272:
                        self.send_chat('You can\'t destroy your team\'s blocks in this area. Attack the enemy\'s tower!')
                        return False
                if self.world_object.position.x <= 288:
                    if self.tool is WEAPON_TOOL:
                        self.send_chat('You must be closer to the enemy\'s base to shoot blocks!')
                        return False
                    if self.tool is GRENADE_TOOL:
                        self.send_chat('You must be closer to the enemy\'s base to grenade blocks!')
                        return False
            if self.team is self.protocol.green_team:
                if self.tool is SPADE_TOOL and self.world_object.position.x >= 301 and self.world_object.position.x <= 384 \
                    and self.world_object.position.y >= 240 and self.world_object.position.y <= 272:
                        self.send_chat('You can\'t destroy your team\'s blocks in this area. Attack the enemy\'s tower!')
                        return False
                if self.world_object.position.x >= 224:
                    if self.tool is WEAPON_TOOL:
                        self.send_chat('You must be closer to the enemy\'s base to shoot blocks!')
                        return False
                    if self.tool is GRENADE_TOOL:
                        self.send_chat('You must be closer to the enemy\'s base to grenade blocks!')
                        return False
            return connection.on_block_destroy(self, x, y, z, mode)

    return BabelProtocol, BabelConnection
