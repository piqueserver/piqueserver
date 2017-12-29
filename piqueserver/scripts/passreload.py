# passreload.py
# written by Danke

from __future__ import print_function
from piqueserver import commands
from piqueserver.commands import command
from piqueserver import cfg
import json
import os.path

# TODO: build an entire config reload core script

@command(admin_only=True)
def reloadconfig(connection):
    new_config = {}
    try:
        new_config = json.load(open(
            os.path.join(cfg.config_dir, cfg.config_file), 'r'))
        if not isinstance(new_config, dict):
            raise ValueError('%s is not a mapping type' % cfg.config_file)
    except ValueError as v:
        print('Error reloading config:', v)
        return 'Error reloading config. Check log for details.'
    # NOTE: this updates the config dictionary, but doesn't update any config -
    # does it actually work?
    connection.protocol.config.update(new_config)
    connection.protocol.reload_passes()
    return 'Config reloaded!'


def apply_script(protocol, connection, config):
    class PassreloadProtocol(protocol):

        def reload_passes(self):
            for password in self.passwords.get('admin', []):
                if not password:
                    self.everyone_is_admin = True
            commands.update_rights(config.get('rights', {}))
    return PassreloadProtocol, connection
