"""
nosharp.py - kicks player whose name starts with # and also kicks player with no name
by kmsi(kmsiapps@gmail.com)
version 1(2017.01.22)
"""


def apply_script(protocol, connection, config):

    class noSharpConnection(connection):

        def on_login(self, name):
            if(len(self.name) == 0 or self.name[0] == '#'):
                self.disconnect()
            return connection.on_login(self, name)
    return protocol, noSharpConnection
