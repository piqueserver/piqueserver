"""
Saves current map on shutdown (and optionally loads it again on startup)

Maintainer: mat^2
"""

import os
from twisted.internet import reactor
from pyspades.vxl import VXLData
from piqueserver import cfg


def get_name(map):
    return '%s/%s.saved.vxl' % (os.path.join(cfg.config_dir, 'maps'), map.rot_info.name)


def apply_script(protocol, connection, config):
    class MapSaveProtocol(protocol):

        def __init__(self, *arg, **kw):
            protocol.__init__(self, *arg, **kw)
            reactor.addSystemEventTrigger('before', 'shutdown', self.save_map)

        def get_map(self, name):
            map = protocol.get_map(self, name)
            if config.get('load_saved_map', False):
                cached_path = get_name(map)
                print("Loading saved map for {} from {}".format(name, cached_path))
                if os.path.isfile(cached_path):
                    map.data = VXLData(open(cached_path, 'rb'))
                    print("Saved map loaded")
            return map

        def save_map(self):
            open(get_name(self.map_info), 'wb').write(self.map.generate())
            print("Map saved to {}".format(get_name(self.map_info)))

    return MapSaveProtocol, connection
