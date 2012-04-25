"""
Adds the ability to 'trust' certain players, i.e. they cannot be votekicked
or rubberbanded.

Maintainer: mat^2 / hompy
"""

from commands import add, admin, get_player

S_GRANTED = '{player} is now trusted'
S_GRANTED_SELF = "You've been granted trust, and can't be votekicked"
S_CANT_VOTEKICK = "{player} is trusted and can't be votekicked"

@admin
def trust(connection, player):
    player = get_player(connection.protocol, player)
    player.on_user_login('trusted', False)
    player.send_chat(S_GRANTED_SELF)
    return S_GRANTED.format(player = player.name)

add(trust)

def apply_script(protocol, connection, config):
    class TrustedConnection(connection):
        def on_user_login(self, user_type, verbose = True):
            if user_type == 'trusted':
                self.speedhack_detect = False
                if (self.protocol.votekick is not None and
                    self.protocol.votekick.target is self):
                    self.protocol.votekick.cancel()
            return connection.on_user_login(self, user_type, verbose)
        
        def make_trusted(self):
            self.speedhack_detect = False
            if (self.protocol.votekick is not None and
                self.protocol.votekick.target is self):
                self.protocol.votekick.cancel()
    
    class TrustedProtocol(protocol):
        def start_votekick(self, payload):
            player = payload.target
            if player.user_types.trusted:
                return S_CANT_VOTEKICK.format(player = player.name)
            return protocol.start_votekick(self, payload)
    
    return TrustedProtocol, TrustedConnection