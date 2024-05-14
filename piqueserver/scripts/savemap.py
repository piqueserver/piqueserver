"""
Adds a /savemap command to save the current state of the map.
You can specify any name with an argument, without it the map will
be saved with the '.saved' suffix.
With /rmsaved you can delete a '.saved' version of this map.

Options
^^^^^^^

.. code-block:: toml

    [savemap]
    # automatically load the saved map on map load
    load_saved_map = true
    # automatically save map at shutdown
    save_at_shutdown = false
    # automatically save map at map rotation or server shutdown
    always_save_map = false
"""

import os
from twisted.internet import reactor
from twisted.logger  import Logger
from piqueserver.config import config
from piqueserver.commands import command
from piqueserver.map import RotationInfo


savemap_config = config.section('savemap')
config_dir = config.config_dir
log = Logger()


@command('savemap', admin_only=True)
def savemap(connection, custom_name=None):
    name = connection.protocol.save_map(custom_name)
    return "Map saved to '%s'" % name

@command('rmsaved', admin_only=True)
def rmsaved(connection):
    name = connection.protocol.map_info.rot_info.name
    path = get_path(name)
    if os.path.isfile(path):
        os.remove(path)
        # remove .saved suffix
        connection.protocol.map_info.rot_info.name = name[:-6]
        return "Map '%s' removed" % name
    else:
        return "There is no saved version of '%s' map" % name

def get_path(map_name):
    if map_name.endswith('.saved'):
        map_name = map_name[:-6]
    return '%s.saved.vxl' % os.path.join(config_dir, 'maps', map_name)

def apply_script(protocol, connection, config):
    class SaveMapProtocol(protocol):
        def __init__(self, *arg, **kw):
            protocol.__init__(self, *arg, **kw)
            def call():
                at_shutdown = savemap_config.option('save_at_shutdown', False).get()
                always = savemap_config.option('always_save_map', False).get()
                if at_shutdown or always:
                    self.save_map()
            reactor.addSystemEventTrigger('before', 'shutdown', call)

        async def set_map_name(self, rot_info: RotationInfo) -> None:
            if savemap_config.option('always_save_map', False).get():
                if self.map is not None:
                    self.save_map()
            if savemap_config.option('load_saved_map', False).get():
                if os.path.isfile(get_path(rot_info.name)):
                    log.info("Saved version of '{name}' found",
                             name=rot_info.name)
                    rot_info.name += '.saved'
            await protocol.set_map_name(self, rot_info)

        def save_map(self, custom_name=None):
            if custom_name:
                path = os.path.join(config_dir, 'maps', custom_name) + '.vxl'
            else:
                path = get_path(self.map_info.rot_info.name)
            with open(path, 'wb') as f:
                f.write(self.map.generate())
            log.info("Map saved to '{path}'", path=path)
            return path

        def update_format(self) -> None:
            if self.map_info.short_name.endswith('.saved'):
                self.map_info.short_name = self.map_info.short_name[:-6]
            protocol.update_format(self)

    return SaveMapProtocol, connection
