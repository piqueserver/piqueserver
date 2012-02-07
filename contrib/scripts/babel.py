from pyspades.constants import *
from random import randint

PLATFORM_WIDTH = 100
PLATFORM_HEIGHT = 32
PLATFORM_COLOR = (128, 128, 128, 255)
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
    if x >= (256 - PLATFORM_WIDTH) and x <= (256 + PLATFORM_WIDTH) and y >= (256 - PLATFORM_HEIGHT) and y <= (256 + PLATFORM_HEIGHT):
        return True
    return False

def apply_script(protocol, connection, config):
    class BabelProtocol(protocol):
        babel = False 
        def on_map_change(self, map):
            extensions = self.map_info.extensions
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
                        map.set_point(x, y, 1, PLATFORM_COLOR, False)
            return protocol.on_map_change(self, map)
        
        def is_indestructable(self, x, y, z):
            if self.babel:
                if z == 1:
                    if coord_on_platform(x, y, z):
                        protocol.is_indestructable(self, x, y, z)
                        return True
            return protocol.is_indestructable(self, x, y, z)
    
    class BabelConnection(connection):
        def on_block_build_attempt(self, x, y, z):
            if not self.god and self.protocol.babel:
                if z <= 2:
                    if coord_on_platform(x, y, z):
                        connection.on_block_build_attempt(self, x, y, z)
                        return False
                if z == 1:
                    if x >= (256 - PLATFORM_WIDTH - 1) and x <= (256 + PLATFORM_WIDTH + 1) \
                       and y >= (256 - PLATFORM_HEIGHT -1) and y <= (256 + PLATFORM_HEIGHT + 1):
                        connection.on_block_build_attempt(self, x, y, z)
                        return False
            return connection.on_block_build_attempt(self, x, y, z)
    
    return BabelProtocol, BabelConnection