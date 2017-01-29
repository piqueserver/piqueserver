"""
Extensions to the map metadata (e.g. water damage).

Maintainer: ?
"""

def apply_script(protocol, connection, config):
    class MapExtensionConnection(connection):
        def on_position_update(self):
            extensions = self.protocol.map_info.extensions
            if (extensions.has_key('water_damage') and
                self.world_object.position.z>=61):
                water_damage = extensions['water_damage']
                self.environment_hit(water_damage)
            if (extensions.has_key('boundary_damage')):
                x = self.world_object.position.x
                y = self.world_object.position.y
                boundary_damage = extensions['boundary_damage']
                if (x<=boundary_damage['left'] or x>=boundary_damage['right'] or
                    y<=boundary_damage['top'] or y>=boundary_damage['bottom']):
                    self.environment_hit(boundary_damage['damage'])
            connection.on_position_update(self)

        def environment_hit(self, value):
            if value < 0 and self.hp >= 100: # do nothing at max health
                return
            self.set_hp(self.hp - value)

        def on_command(self, command, parameters):
            disabled = self.protocol.map_info.extensions.get(
                'disabled_commands', [])
            if command in disabled:
                self.send_chat("Command '%s' disabled for this map" % command)
                return
            return connection.on_command(self, command, parameters)

    return protocol, MapExtensionConnection
