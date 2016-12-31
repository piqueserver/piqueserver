# passreload.py
# written by Danke

import commands
from commands import add, admin
import json

@admin
def reloadconfig(connection):
    new_config = {}
    try:
        new_config = json.load(open('config.txt', 'r'))
        if not isinstance(new_config, dict):
            raise ValueError('config.txt is not a mapping type')
    except ValueError, v:
        print 'Error reloading config:', v
        return 'Error reloading config. Check pyspades log for details.'
    connection.protocol.config.update(new_config)
    connection.protocol.reload_passes()
    return 'Config reloaded!'

add(reloadconfig)

def apply_script(protocol, connection, config):
    class PassreloadProtocol(protocol):
        def reload_passes(self):
            self.passwords = config.get('passwords', {})
            for password in self.passwords.get('admin', []):
                if password == 'replaceme':
                    print 'REMEMBER TO CHANGE THE DEFAULT ADMINISTRATOR PASSWORD!'
                elif not password:
                    self.everyone_is_admin = True
            commands.rights.update(config.get('rights', {}))
    return PassreloadProtocol, connection
