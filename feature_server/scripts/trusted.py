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
    has_votekick = 'votekick' in config.get('scripts', [])
    class TrustedConnection(connection):
        def on_user_login(self, user_type, verbose = True):
            if user_type == 'trusted':
                self.speedhack_detect = False
                if (has_votekick and self.protocol.vk_target is self):
                    self.protocol.votekick_show_result("Trusted user")
                    self.protocol.votekick_cleanup()
            return connection.on_user_login(self, user_type, verbose)
        if has_votekick:
            def start_votekick(self, target, reason = None):
                if target.user_types.trusted:
                    return S_CANT_VOTEKICK.format(player = target.name)
                return connection.start_votekick(self, target, reason)
            def cancel_verify(self, instigator):
                return (connection.cancel_verify(self, instigator) or
                        (self.user_types.trusted and
                         self.protocol.vk_target is self))
    
    return protocol, TrustedConnection
