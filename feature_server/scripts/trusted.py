from commands import add, admin, get_player

@admin
def trust(connection, player):
    player = get_player(connection.protocol, player)
    player.trusted = True
    player.speedhack_detect = False
    player.send_chat("You're now a trusted user.")
    return '%s is now trusted' % player.name

add(trust)

def apply_script(protocol, connection, config):
    class TrustedConnection(connection):
        trusted = False
        
        def on_user_login(self, user_type):
            if user_type == 'trusted':
                self.trusted = True
                self.speedhack_detect = False
                self.protocol.irc_say('* %s logged in as %s' %
                    (self.name, user_type))
                if self.protocol.votekick_player is self:
                    self.protocol.votekick_call.cancel()
                    self.protocol.end_votekick(False, 'Player is trusted')
                return 'Logged in as trusted user'
            return connection.on_user_login(self, user_type)
    
    class TrustedProtocol(protocol):
        def start_votekick(self, payload):
            player = payload.target
            if player.trusted:
                return "%s is trusted and you can't votekick him." % player.name
            return protocol.start_votekick(self, payload)
    
    return TrustedProtocol, TrustedConnection
