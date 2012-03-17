from pyspades.constants import *

def apply_script(protocol, connection, config):
    
    class StrongBlockConnection(connection):
        def on_connect(self):
            self.strong_block_hits = 0
            return connection.on_connect(self)
        def on_block_destroy(self, x, y, z, value):
            self.strong_block_hits += 1
            if self.strong_block_hits >= self.protocol.hits_per_block:
                self.strong_block_hits = 0
                if value == DESTROY_BLOCK:
                    self.send_chat("Your spade is weak! Try right clicking.")
                return connection.on_block_destroy(self, x, y, z, value)
            else:
                return False
    
    class StrongBlockProtocol(protocol):
        hits_per_block = config.get('hits_per_block', 2)
    
    return StrongBlockProtocol, StrongBlockConnection
