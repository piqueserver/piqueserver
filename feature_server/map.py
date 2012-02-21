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

from pyspades.load import VXLData

import os
import imp
import math
import random

DEFAULT_LOAD_DIR = './maps'

class MapNotFound(IOError):
    pass

def get_map_filename(name, load_dir = DEFAULT_LOAD_DIR):
    return os.path.join(load_dir, '%s.vxl' % name)

def get_meta_filename(name, load_dir = DEFAULT_LOAD_DIR):
    return os.path.join(load_dir, '%s.txt' % name)

def check_rotation(maps, load_dir = DEFAULT_LOAD_DIR):
    for map in maps:
        map = map.split("#")[0].strip()
        if (not os.path.isfile(get_map_filename(map, load_dir)) 
        and not os.path.isfile(get_meta_filename(map, load_dir))):
            raise MapNotFound('map %s does not exist' % map)

class Map(object):
    def __init__(self, name, load_dir = DEFAULT_LOAD_DIR):
        seedsplit = name.split("#")
        if len(seedsplit) > 1: # user specified a seed
            basename = seedsplit[0].strip()
            seed = int(seedsplit[1])
        else: # manufacture a reproducable seed value
            basename = name
            random.seed()
            seed = random.randint(0, math.pow(2, 31))
        
        self.load_information(basename, load_dir)
        
        if self.gen_script:
            # retitle the map with the seed
            self.name = basename + " #%s" % seed
            print "Generating map '%s'..." % self.name
            random.seed(seed)
            self.data = self.gen_script(basename, seed)
        else:
            print "Loading map '%s'..." % self.name
            self.load_vxl(basename, load_dir)

        print 'Map loaded successfully.'

    def load_information(self, name, load_dir):
        info_file = get_meta_filename(name, load_dir)
        try:
            info = imp.load_source(name, info_file)
        except IOError:
            info = None
        self.info = info
        self.name = getattr(info, 'name', name)
        self.author = getattr(info, 'author', '(unknown)')
        self.version = getattr(info, 'version', '1.0')
        self.description = getattr(info, 'description', '')
        self.extensions = getattr(info, 'extensions', {})
        self.script = getattr(info, 'apply_script', None)
        self.gen_script = getattr(info, 'gen_script', None)
        self.time_limit = getattr(info, 'time_limit', None)
        self.cap_limit = getattr(info, 'cap_limit', None)
        self.get_spawn_location = getattr(info, 'get_spawn_location', None)
        self.get_entity_location = getattr(info, 'get_entity_location', None)
        self.on_map_change = getattr(info, 'on_map_change', None)
        self.on_map_leave = getattr(info, 'on_map_leave', None)
        self.on_block_destroy = getattr(info, 'on_block_destroy', None)
        self.is_indestructable = getattr(info, 'is_indestructable', None)
        
    def apply_script(self, protocol, connection, config):
        if self.script is not None:
            protocol, connection = self.script(protocol, connection, config)
        return protocol, connection

    def load_vxl(self, name, load_dir):
        try:
            fp = open(get_map_filename(name, load_dir), 'rb')
        except OSError:
            raise MapNotFound('map %s does not exist' % name)
        self.data = VXLData(fp)
        fp.close()
