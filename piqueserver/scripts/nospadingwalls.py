from pyspades.constants import SPADE_TOOL
from piqueserver.commands import command


@command('togglewallspading', 'tws', admin_only=True)
def togglewallspading(self):
    self.protocol.is_fluffy = not self.protocol.is_fluffy
    if not self.protocol.is_fluffy:
        return 'Spading someone behind a wall is possible again now!'
    else:
        return 'You canot spade people through walls anymore. (killjoy)'


def apply_script(protocol, connection, config):

    class nowallspadingprotocol(protocol):
        is_fluffy = True

    class nowallspadingconnection(connection):

        def on_hit(self, hit_amount, hit_player, hit_type, grenade):

            if hit_player.protocol.is_fluffy:
                pos = hit_player.world_object.position

                if not self.world_object.can_see(
                        pos.x,
                        pos.y,
                        pos.z) and self.tool == SPADE_TOOL and not grenade and self.team != hit_player.team:
                    return False

            return connection.on_hit(
                self, hit_amount, hit_player, hit_type, None)

    return nowallspadingprotocol, nowallspadingconnection
