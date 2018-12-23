"""
Allows reloading config on the fly

Commands
^^^^^^^^

* ``/reloadconfig`` reloads the config (also updates rights) *admin only*

.. codeauthor:: Danke
"""

import json
import os.path

from piqueserver import commands
from piqueserver.commands import command
from piqueserver.config import config
from piqueserver.auth import auth

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
            for conn in list(self.connections.values()):
                for user_type in conn.user_types:
                    # updates connections's rights set
                    auth.set_user_type(conn, user_type)


    return PassreloadProtocol, connection
