"""
Team Deathmatch game mode.

Options
^^^^^^^
.. code-block:: toml
    [tdm]
    # Maximum kills to win the game
    kill_limit = 100

    # How many points you will get by intel capture
    intel_points = 10

    # Hide intel from the map and disable the captures
    remove_intel = false

    # Use intel scores as a percentage to win the game
    # This can cause trouble if remove_intel is false
    score_percentage = false

..Maintainer: Triplefox
"""

from pyspades.constants import *
from pyspades.contained import IntelCapture
from piqueserver.config import config
from piqueserver.commands import command
import math

TDM_CONFIG = config.section("tdm")
KILL_LIMIT = TDM_CONFIG.option("kill_limit", default=100)
INTEL_POINTS = TDM_CONFIG.option("intel_points", default=10)
REMOVE_INTEL = TDM_CONFIG.option("remove_intel", default=False)
SCORE_PERCENTAGE = TDM_CONFIG.option("score_percentage", default=False)

HIDE_COORD = (0, 0, 0)


@command()
def score(connection):
    return connection.protocol.get_kill_count()


def apply_script(protocol, connection, config):
    class TDMConnection(connection):

        def on_spawn(self, pos):
            self.send_chat(self.explain_game_mode())
            self.send_chat(self.protocol.get_kill_count())
            return connection.on_spawn(self, pos)

        def on_flag_take(self):
            if REMOVE_INTEL.get():
                return False
            return connection.on_flag_take(self)

        def on_flag_capture(self):
            result = connection.on_flag_capture(self)
            self.team.kills += INTEL_POINTS.get()
            self.protocol.check_end_game(self)
            return result

        def on_kill(self, killer, type, grenade):
            result = connection.on_kill(self, killer, type, grenade)
            self.protocol.check_end_game(killer)
            return result

        def explain_game_mode(self):
            msg = 'Team Deathmatch: Kill the opposing team.'
            if not REMOVE_INTEL.get():
                msg += ' Intel is worth %s kills.' % INTEL_POINTS.get()
            return msg

    class TDMProtocol(protocol):
        game_mode = CTF_MODE

        def on_flag_spawn(self, x, y, z, flag, entity_id):
            if REMOVE_INTEL.get():
                return HIDE_COORD
            return protocol.on_flag_spawn(self, x, y, z, flag, entity_id)

        def get_kill_count(self):
            green_kills = self.green_team.kills
            blue_kills = self.blue_team.kills
            diff = green_kills - blue_kills
            if green_kills > blue_kills:
                return ("%s leads %s-%s (+%s, %s left). Playing to %s kills." %
                        (self.green_team.name,
                         green_kills, blue_kills,
                         diff,
                         KILL_LIMIT.get() - green_kills,
                         KILL_LIMIT.get()))
            elif green_kills < blue_kills:
                return ("%s leads %s-%s (+%s, %s left). Playing to %s kills." %
                        (self.blue_team.name,
                         blue_kills, green_kills,
                         -diff,
                         KILL_LIMIT.get() - blue_kills,
                         KILL_LIMIT.get()))
            else:
                return ("%s-%s, %s left. Playing to %s kills." %
                        (green_kills,
                         blue_kills,
                         KILL_LIMIT.get() - green_kills,
                         KILL_LIMIT.get()))

        # since its a team based game, we gonna split the caps
        # for all players in the team
        def do_captures(self, team, caps):
            while (team.score < caps):
                for player in team.get_players():
                    if team.score >= caps:
                        break

                    team.score += 1
                    intel_capture = IntelCapture()
                    intel_capture.player_id = player.player_id
                    intel_capture.winning = False

                    self.broadcast_contained(intel_capture)

        def check_end_game(self, player):
            if SCORE_PERCENTAGE.get() and player:
                team = player.team
                caps_percent = math.floor(
                    self.max_score*team.kills/KILL_LIMIT.get())

                if caps_percent > team.score:
                    self.do_captures(team, caps_percent)

            if self.green_team.kills >= KILL_LIMIT.get():
                self.broadcast_chat("%s Team Wins, %s - %s" %
                                    (self.green_team.name,
                                     self.green_team.kills,
                                     self.blue_team.kills))
                self.reset_game(player)
                protocol.on_game_end(self)
            elif self.blue_team.kills >= KILL_LIMIT.get():
                self.broadcast_chat("%s Team Wins, %s - %s" %
                                    (self.blue_team.name,
                                     self.blue_team.kills,
                                     self.green_team.kills))
                self.reset_game(player)
                protocol.on_game_end(self)

    return TDMProtocol, TDMConnection
