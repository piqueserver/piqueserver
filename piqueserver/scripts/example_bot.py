"""
example_bot — a minimal bot that roams toward enemies and shoots on sight.

Add "example_bot" to the scripts list in config.toml to enable it.
"""

from twisted.internet import reactor

from piqueserver.bot import Bot, BotManagerMixin
from pyspades.constants import RIFLE_WEAPON


class ExampleBot(Bot):
    def think(self, _dt: float) -> None:
        enemies = self.get_enemies()
        if not enemies:
            return

        target = self.closest(enemies)
        self.look_toward(target)

        if self.can_see(target):
            self.shoot_at(target)
        else:
            # walk toward the enemy when out of sight
            self.set_walk(up=True)


def apply_script(protocol, connection, _config):
    class BotProtocol(BotManagerMixin, protocol):
        def on_map_change(self, map_):
            super().on_map_change(map_)
            # Defer bot creation to the next event loop tick so set_map()
            # finishes clearing protocol state before we register new players.
            reactor.callLater(0, self._spawn_bots)

        def _spawn_bots(self):
            self.add_bot(ExampleBot.create(self, "ExampleBot", self.team_1, RIFLE_WEAPON))

    return BotProtocol, connection
