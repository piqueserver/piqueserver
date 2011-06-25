import commands

@commands.name('trustedlogin')
def trusted_login(connection, password):
    if password in connection.protocol.trusted_passwords:
        connection.trusted = True
        return 'Logged in as trusted user.'
    return 'Invalid password.'

commands.add(trusted_login)

def apply_script(protocol, connection, config):
    passwords = config.get('passwords', {}).get('trusted', [])
    
    class ProtectConnection(connection):
        trusted = False
    
    class ProtectProtocol(protocol):
        trusted_passwords = passwords
        
        def start_votekick(self, connection, player):
            if player.trusted:
                return 'Cannot votekick a trusted player.'
            return protocol.start_votekick(self, connection, player)
        
    return ProtectProtocol, ProtectConnection