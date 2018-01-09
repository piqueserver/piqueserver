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

import os
import imp
import math
import random

from pyspades.vxl import VXLData
from piqueserver import cfg


class MapNotFound(Exception):

    def __init__(self, the_map):
        self.map = the_map
        Exception.__init__(self, 'map %s does not exist' % the_map)

    def __nonzero__(self):
        return False


def check_rotation(maps, load_dir=None):
    """
    Checks if provided maps exist in maps dir. and
    returns an array of RotationInfo objects for those maps.
    Raises MapNotFound exception if maps are not found.
    """
    if load_dir is None:
        load_dir = os.path.join(cfg.config_dir, 'maps')
    infos = []
    for the_map in maps:
        if not isinstance(the_map, RotationInfo):
            the_map = RotationInfo(the_map)
        infos.append(the_map)
        if (not os.path.isfile(the_map.get_map_filename(load_dir))
                and not os.path.isfile(the_map.get_meta_filename(load_dir))):
            raise MapNotFound(the_map)
    return infos


class Map(object):
    # pylint: disable=too-many-instance-attributes

    def __init__(self, rot_info, load_dir):
        self.load_information(rot_info, load_dir)

        if self.gen_script:
            seed = rot_info.get_seed()
            self.name = '%s #%s' % (rot_info.name, seed)
            print("Generating map '%s'..." % self.name)
            random.seed(seed)
            self.data = self.gen_script(rot_info.name, seed)
        else:
            print("Loading map '%s'..." % self.name)
            self.load_vxl(rot_info)

        print('Map loaded successfully.')

    def load_information(self, rot_info, load_dir):
        self.load_dir = load_dir
        try:
            info = imp.load_source(
                'piqueserver_internal_map_' + rot_info.name, rot_info.get_meta_filename(load_dir))
        except IOError:
            info = None
        self.info = info
        self.rot_info = rot_info
        self.gen_script = getattr(info, 'gen_script', None)
        if self.gen_script:
            self.short_name = rot_info.name
            self.name = rot_info.full_name
        else:
            self.name = getattr(info, 'name', self.rot_info.name)
            self.short_name = self.name
        self.author = getattr(info, 'author', '(unknown)')
        self.version = getattr(info, 'version', '1.0')
        self.description = getattr(info, 'description', '')
        self.extensions = getattr(info, 'extensions', {})
        self.script = getattr(info, 'apply_script', None)
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

    def load_vxl(self, rot_info):
        try:
            fp = open(rot_info.get_map_filename(self.load_dir), 'rb')
        except OSError:
            raise MapNotFound(rot_info.name)
        self.data = VXLData(fp)
        fp.close()


class RotationInfo(object):
    seed = None

    def __init__(self, name="pyspades"):
        self.full_name = name

        splitted = name.split("#")
        if len(splitted) > 1:  # user specified a seed
            name = splitted[0].strip()
            self.seed = int(splitted[1])
        self.name = name

    def get_seed(self):
        if self.seed is not None:
            return self.seed
        random.seed()
        return random.randint(0, math.pow(2, 31))

    def get_map_filename(self, load_dir):
        return os.path.join(load_dir, '%s.vxl' % self.name)

    def get_meta_filename(self, load_dir):
        return os.path.join(load_dir, '%s.txt' % self.name)

    def __str__(self):
        return self.full_name
