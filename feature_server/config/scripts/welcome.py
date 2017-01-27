"""
Greets specified people entering with messages

Maintainer: mat^2
"""


def apply_script(protocol, connection, config):
    welcomes = config.get('welcomes', {})

    class EnterConnection(connection):

        def on_login(self, name):
            if name in welcomes:
                self.protocol.send_chat(welcomes[name])
            connection.on_login(self, name)
    return protocol, EnterConnection
