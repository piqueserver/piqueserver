SMARTNADE_DELAY = 0.5

def apply_script(protocol, connection, config):
    class SmartNadeProtocol(protocol):
        def on_world_update(self):
            for player in self.players.values():
                for nade in player.smart_nades:
                    if nade.fuse > SMARTNADE_DELAY:
                        for enemy in player.team.other.get_players():
                            if nade.get_damage(enemy.world_object.position) != 0:
                                nade.fuse = min(nade.fuse, SMARTNADE_DELAY)
            return protocol.on_world_update(self)

    class SmartNadeConnection(connection):
        def __init__(self, *arg, **kw):
            connection.__init__(self, *arg, **kw)
            self.smart_nades = []

        def on_grenade_thrown(self, grenade):
            self.smart_nades.append(grenade)
            return connection.on_grenade_thrown(self, grenade)

        def grenade_exploded(self, grenade):
            self.smart_nades.remove(grenade)
            return connection.grenade_exploded(self, grenade)

    return SmartNadeProtocol, SmartNadeConnection
