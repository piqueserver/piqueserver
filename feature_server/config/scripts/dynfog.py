import commands

def apply_script(protocol, connection, config):
    class FogProtocol(protocol):
        default_fog = (128, 232, 255)
        def on_map_change(self, name):
            self.set_fog_color(getattr(self.map_info.info, 'fog', self.default_fog))
            protocol.on_map_change(self, name)
    return FogProtocol, connection
