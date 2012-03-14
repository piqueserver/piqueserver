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

from pyspades.vxl import VXLData

import os
import imp
import math
import random

DEFAULT_LOAD_DIR = './maps'

class MapNotFound(IOError):
    pass

def check_rotation(maps, load_dir = DEFAULT_LOAD_DIR):
    nmaps = []
    for map in maps:
        if type(map) is not RotationInfo:
            map = RotationInfo(map)
        nmaps.append(map)
        if (not os.path.isfile(map.map(load_dir))
        and not os.path.isfile(map.meta(load_dir))):
            raise MapNotFound('map %s does not exist' % map)
    return nmaps

class Map(object):
    def __init__(self, rot_info, load_dir = DEFAULT_LOAD_DIR):

        self.load_information(rot_info, load_dir)
        
        if self.gen_script and rot_info.seed is not None:
            self.name = '%s #%s' % (rot_info.file, rot_info.seed)
            print "Generating map '%s'..." % self.name
            random.seed(rot_info.seed)
            self.data = self.gen_script(rot_info.file, rot_info.seed)
        else:
            print "Loading map '%s'..." % self.name
            self.load_vxl(rot_info, load_dir)

        print 'Map loaded successfully.'

    def load_information(self, rot_info, load_dir):
        try:
            info = imp.load_source(rot_info.file, rot_info.meta())
        except IOError:
            info = None
        self.info = info
        self.rot_info = rot_info
        self.name = getattr(info, 'name', self.rot_info.file)
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

        if self.gen_script:
            self.name = self.rot_info.text
        
    def apply_script(self, protocol, connection, config):
        if self.script is not None:
            protocol, connection = self.script(protocol, connection, config)
        return protocol, connection

    def load_vxl(self, rot_info, load_dir):
        try:
            fp = open(rot_info.map(load_dir), 'rb')
        except OSError:
            raise MapNotFound('map %s does not exist' % rot_info.text)
        self.data = VXLData(fp)
        fp.close()

class RotationInfo(object):
    def __init__(self, text = "pyspades"):
        self.text = text
        
        seedsplit = text.split("#")
        if len(seedsplit) > 1: # user specified a seed
            basename = seedsplit[0].strip()
            seed = int(seedsplit[1])
        else: # manufacture a reproducable seed value
            basename = text
            random.seed()
            seed = random.randint(0, math.pow(2, 31))
        self.file = basename
        self.seed = seed
        
    def map(self, load_dir = DEFAULT_LOAD_DIR):
        return os.path.join(load_dir, '%s.vxl' % self.file)
    def meta(self, load_dir = DEFAULT_LOAD_DIR):
        return os.path.join(load_dir, '%s.txt' % self.file)
