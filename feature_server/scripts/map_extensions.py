from pyspades.constants import HIT_CONSTANTS
from pyspades.server import hit_packet

def apply_script(protocol, connection, config):
    class MapExtensionConnection(connection):
        def on_update_position(self):
            water_damage = self.protocol.map_info.extensions['water_damage']
            if (self.speed_limit_grace<1 and
                water_damage and
                self.position.z>=61):
                self.environment_hit()
            connection.on_update_position(self)
        
        def environment_hit(self):
            value = 25
            self.hp -= value
            if self.hp <= 0:
                self.kill()
                return
            hit_packet.value = HIT_CONSTANTS[value]
            self.send_contained(hit_packet)
    
    return protocol, MapExtensionConnection