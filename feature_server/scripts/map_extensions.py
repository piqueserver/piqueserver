from pyspades.server import hit_packet

def apply_script(protocol, connection, config):
    
    class MapExtensionConnection(connection):
        def on_update_position(self):
            extensions = self.protocol.map_info.extensions
            if (extensions.has_key('water_damage') and
                self.position.z>=61):
                water_damage = extensions['water_damage']                
                self.environment_hit(water_damage)
            connection.on_update_position(self)
    
        def environment_hit(self, value):
            if value<0 and self.hp >= 100: # do nothing at max health
                return
            self.hp -= value
            if self.hp <= 0:
                self.kill()
                return
            if self.hp > 100: # limit health gains
                self.hp = 100
            hit_packet.hp = self.hp
            self.send_contained(hit_packet)

    return protocol, MapExtensionConnection