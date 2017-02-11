"""
nosharp.py - kicks player whose name starts with # and also kicks player with no name
by kmsi(kmsiapps@gmail.com)
version 3(2017.02.06)
 - Added options
 - Now puts player on spectator team instead of kicking
 - Auto-disconnects after specific time(default : 10 seconds)
"""
from twisted.internet import reactor


def apply_script(protocol, connection, config):
    class noSharpConnection(connection):

        def on_spawn(self, pos):

            block_noname = True
            block_sharpname = True
            autokick_duration = 10  # seconds
            # Edit here to change options

            autokick_call = None

            if len(self.name) == 0:
                if block_noname:
                    self.set_team(self.protocol.spectator_team)
                    self.send_chat('%% Your name is empty. Will be kicked soon.')
                    self.autokick_call = reactor.callLater(autokick_duration, self.autokick)

            elif block_sharpname and self.name[0] == '#':
                self.set_team(self.protocol.spectator_team)
                self.send_chat('%% Your name starts with #. Will be kicked soon.')
                self.autokick_call = reactor.callLater(autokick_duration, self.autokick)
            else:
                return connection.on_spawn(self, pos)

        def autokick(self):
            self.autokick_call = None
            self.kick('Invalid name')

    return protocol, noSharpConnection
