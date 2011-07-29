def apply_script(protocol, connection, config):
    class TrustedConnection(connection):
        trusted = False
        
        def on_user_login(self, user_type):
            if user_type == 'trusted':
                self.trusted = True
                self.speedhack_detect = False
                self.protocol.irc_say('* %s logged in as %s' %
                    (self.name, user_type))
                return 'Logged in as trusted user'
            return connection.on_user_login(self, user_type)
    
    class TrustedProtocol(protocol):
        def start_votekick(self, connection, player, reason = None):
            if player.trusted:
                return "%s is trusted and you can't votekick him." % player.name
            return protocol.start_votekick(self, connection, player, reason)
    
    return TrustedProtocol, TrustedConnection