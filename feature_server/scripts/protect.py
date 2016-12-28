"""
Protects areas against block destroying/building.

Maintainer: hompy
"""

from commands import add, admin
from pyspades.common import coordinates

@admin
def protect(connection, value = None):
    protocol = connection.protocol
    if value is None:
        protocol.protected = None
        protocol.send_chat('All areas unprotected', irc = True)
    else:
        if protocol.protected is None:
            protocol.protected = set()
        pos = coordinates(value)
        protocol.protected.symmetric_difference_update([pos])
        message = 'The area at %s is now %s' % (value.upper(),
            'protected' if pos in protocol.protected else 'unprotected')
        protocol.send_chat(message, irc = True)

add(protect)

def apply_script(protocol, connection, config):
    class ProtectConnection(connection):
        def _block_available(self, x, y, z):
            if not self.god and self.protocol.is_protected(x, y, z):
                return False
        
        def on_block_build_attempt(self, x, y, z):
            if not self.god and self.protocol.is_protected(x, y, z):
                return False
            return connection.on_block_build_attempt(self, x, y, z)
        
        def on_line_build_attempt(self, points):
            if not self.god:
                for point in points:
                    if self.protocol.is_protected(*point):
                        return False
            return connection.on_line_build_attempt(self, points)
    
    class ProtectProtocol(protocol):
        protected = None
        
        def on_map_change(self, map):
            self.protected = set(coordinates(s) for s in
                getattr(self.map_info.info, 'protected', []))
            protocol.on_map_change(self, map)
        
        def is_indestructable(self, x, y, z):
            if self.is_protected(x, y, z):
                return True
            return protocol.is_indestructable(self, x, y, z)
        
        def is_protected(self, x, y, z):
            if self.protected:
                for sx, sy in self.protected:
                    if x >= sx and y >= sy and x < sx + 64 and y < sy + 64:
                        return True
            return False
    
    return ProtectProtocol, ProtectConnection