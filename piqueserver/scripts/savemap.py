"""
Saves current map on shutdown (and optionally loads it again on startup)

Options
^^^^^^^

.. code-block:: guess

    [savemap]
    load_saved_map = false

.. codeauthor:: mat^2
"""

import os
from twisted.internet import reactor, threads
from twisted.internet.defer import ensureDeferred
from twisted.logger  import Logger
from pyspades.vxl import VXLData
from piqueserver.config import config

log = Logger()

savemap_config = config.section('savemap')
LOAD_SAVED_MAP_OPTION = savemap_config.option('load_saved_map', False)


def get_name(map_info):
    return '%s/%s.saved.vxl' % (os.path.join(config.config_dir, 'maps'),
                                map_info.rot_info.name)


def load_map_from_path(path):
    with open(path, 'rb') as f:
        return VXLData(f)


def apply_script(protocol, connection, config):
    class MapSaveProtocol(protocol):

        def __init__(self, *arg, **kw):
            protocol.__init__(self, *arg, **kw)
            reactor.addSystemEventTrigger('before', 'shutdown', self.save_map)

        def make_map(self, name):
            if not LOAD_SAVED_MAP_OPTION.get():
                # just do the normal operation
                return protocol.make_map(self, name)

            async def do_load():
                map_info = await protocol.make_map(self, name)
                cached_path = get_name(map_info)

                if not os.path.isfile(cached_path):
                    # no cache file. Just load the regular map
                    return map_info

                log.info("Loading saved map for {name} from {cached_path}",
                    name=name, cached_path=cached_path)
                map_info.data = await threads.deferToThread(
                    load_map_from_path, cached_path)
                log.info("Saved map loaded")
                return map_info

            # replace the map_info deferred with our own one that also
            # loads and replaces the map data
            return ensureDeferred(do_load)

        def save_map(self):
            with open(get_name(self.map_info), 'wb') as f:
                f.write(self.map.generate())
            log.info("Map saved to {}".format(get_name(self.map_info)))

    return MapSaveProtocol, connection
