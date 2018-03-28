"""
Greets specified people entering with messages

Maintainer: mat^2
"""
from piqueserver.config import config

welcome_config = config.section("welcome")
welcomes_option = welcome_config.option("welcomes", {})


def apply_script(protocol, connection, config):
    welcomes = welcomes_option.get()

    class EnterConnection(connection):

        def on_login(self, name):
            if name in welcomes:
                self.protocol.send_chat(welcomes[name])
            connection.on_login(self, name)
    return protocol, EnterConnection
