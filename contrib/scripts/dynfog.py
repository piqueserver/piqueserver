import commands

def apply_script(protocol, connection, config):
    class FogProtocol(protocol):
        default_fog = (128, 232, 255)
        def on_map_change(self, name):
            if hasattr(self.map_info.info, 'fog'):
                self.set_fog_color(getattr(self.map_info.info, 'fog'))
            else:
                self.set_fog_color(self.default_fog)
    return FogProtocol, connection