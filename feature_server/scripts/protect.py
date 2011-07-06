from commands import add, admin
from pyspades.common import coordinates

@admin
def protect(connection, value = None):
    if value is None:
        connection.protocol.protected = None
        connection.protocol.send_chat('All areas unprotected.', irc = True)
    else:
        if connection.protocol.protected is None:
            connection.protocol.protected = set()
        pos = coordinates(value)
        connection.protocol.protected.symmetric_difference_update([pos])
        connection.protocol.send_chat('The area at %s is now %sprotected.' %
            (value.upper(), 'un' if pos not in connection.protocol.protected
            else ''), irc = True)

add(protect)

def apply_script(protocol, connection, config):
    class ProtectConnection(connection):
        def on_block_build_attempt(self, x, y, z):
            if not self.god and self.protocol.is_protected(x, y):
                return False
            return connection.on_block_build_attempt(self, x, y, z)
    
    class ProtectProtocol(protocol):
        protected = None
        
        def is_indestructable(self, x, y, z):
            if self.is_protected(x, y):
                return True
            return protocol.is_indestructable(self, x, y, z)
        
        def is_protected(self, x, y):
            if self.protected is None:
                return
            for sx, sy in self.protected:
                if x >= sx and y >= sy and x < sx + 64 and y < sy + 64:
                    return True
    
    return ProtectProtocol, ProtectConnection