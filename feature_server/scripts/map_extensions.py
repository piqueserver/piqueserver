from pyspades.server import hit_packet

def apply_script(protocol, connection, config):
    
    class MapExtensionConnection(connection):
        def on_position_update(self):
            extensions = self.protocol.map_info.extensions
            if (extensions.has_key('water_damage') and
                self.world_object.position.z>=61):
                water_damage = extensions['water_damage']                
                self.environment_hit(water_damage)
            connection.on_position_update(self)
    
        def environment_hit(self, value):
            if value < 0 and self.hp >= 100: # do nothing at max health
                return
            self.set_hp(self.hp - value)

    return protocol, MapExtensionConnection