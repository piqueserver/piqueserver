# passreload.py
# written by Danke

import json
import os.path

from piqueserver import commands
from piqueserver.commands import command
from piqueserver.config import config

# TODO: build an entire config reload core script


@command(admin_only=True)
def reloadconfig(connection):
    try:
        extension = os.path.splitext(config.config_file)[1][1:]
        with open(config.config_file) as fobj:
            config.update_from_file(fobj, format_=extension.upper())
    except Exception as e:
        print('Error reloading config:', e)
        return 'Error reloading config. Check log for details.'
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
