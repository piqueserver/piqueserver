"""
Restocks the user when reloading / throwing a nade.

Commands
^^^^^^^^

* ``/toggledemo`` toggles demolition

.. codeauthor:: learn_more (MIT LICENSE)
"""

from piqueserver.commands import command, admin

DEMOLITION_ENABLED_AT_ROUND_START = False


@command(admin_only=True)
def toggledemo(connection):
    connection.protocol.demolitionEnabled = not connection.protocol.demolitionEnabled
    message = 'Demolition is now disabled'
    if connection.protocol.demolitionEnabled:
        message = 'Demolition is now enabled'
    connection.protocol.send_chat(message, irc=True)
    return 'ok :)'


def apply_script(protocol, connection, config):
    class DemolitionProtocol(protocol):
        demolitionEnabled = DEMOLITION_ENABLED_AT_ROUND_START

        def on_map_change(self, map):
            self.demolitionEnabled = DEMOLITION_ENABLED_AT_ROUND_START
            return protocol.on_map_change(self, map)

    class DemolitionConnection(connection):

        def _on_reload(self):
            if self.protocol.demolitionEnabled:
                self.refill()
            return connection._on_reload(self)

        def on_grenade_thrown(self, grenade):
            if self.protocol.demolitionEnabled:
                self.refill()
            return connection.on_grenade_thrown(self, grenade)

        def on_spawn(self, pos):
            if self.protocol.demolitionEnabled:
                self.send_chat(
                    'You are the demolition man, grenades & ammo will be restocked!')
            return connection.on_spawn(self, pos)

    return DemolitionProtocol, DemolitionConnection
