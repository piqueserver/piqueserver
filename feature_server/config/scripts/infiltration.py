"""
Attackers get ATTACKER_SCORE_MULTIPLIER points for taking and capturing
the intel.

Defenders gain 1 point for every DEFENDER_SCORE_INTERVAL seconds that the intel
remains untouched.

To use set game_mode to 'infiltration' in config.txt, do NOT add to script list.

Maintainer: TheGrandmaster / hompy
"""

from twisted.internet.reactor import callLater
from twisted.internet.task import LoopingCall
from pyspades.server import create_player, player_left, intel_capture
from pyspades.constants import *

ATTACKER_TEAM = 1 # 0 = blue, 1 = green
ATTACKER_TO_DEFENDER_RATIO = 2.0
ATTACKER_SCORE_MULTIPLIER = 10
DEFENDER_SCORE_INTERVAL = 30 # seconds
ON_FLAG_TAKE_FLASHES_FOG = True

S_TEAM_FULL = 'Team full! The defending team always has less players'
S_ATTACKER_OBJECTIVE = '*** ATTACKERS: Infiltrate the enemy base and steal ' \
    'the intel!'
S_DEFENDER_OBJECTIVE = '*** DEFENDERS: Hold your ground! Earn points by ' \
    'keeping the intel safe'
S_OBJECTIVES = {
    ATTACKER_TEAM : S_ATTACKER_OBJECTIVE,
    1 - ATTACKER_TEAM : S_DEFENDER_OBJECTIVE
}

class DummyPlayer():
    protocol = None
    team = None
    player_id = None

    def __init__(self, protocol, team):
        self.protocol = protocol
        self.team = team
        self.acquire_player_id()

    def acquire_player_id(self):
        max_players = min(32, self.protocol.max_players)
        if len(self.protocol.connections) >= max_players:
            try:
                self.player_id = next(self.team.get_players()).player_id
            except StopIteration:
                self.player_id = None
            return self.player_id is not None
        self.player_id = self.protocol.player_ids.pop()
        self.protocol.player_ids.put_back(self.player_id) # just borrowing it!
        create_player.x = 0
        create_player.y = 0
        create_player.z = 63
        create_player.weapon = RIFLE_WEAPON
        create_player.player_id = self.player_id
        create_player.name = self.team.name
        create_player.team = self.team.id
        self.protocol.send_contained(create_player, save = True)
        return True

    def score(self):
        if self.protocol.game_mode != CTF_MODE:
            return
        if self.player_id in self.protocol.players:
            self.acquire_player_id()
        if self.player_id is None and not self.acquire_player_id():
            return
        winning = (self.protocol.max_score not in (0, None) and
            self.team.score + 1 >= self.protocol.max_score)
        self.team.score += 1
        intel_capture.player_id = self.player_id
        intel_capture.winning = winning
        self.protocol.send_contained(intel_capture, save = True)
        if winning:
            self.team.initialize()
            self.team.other.initialize()
            for entity in self.protocol.entities:
                entity.update()
            for player in self.protocol.players.values():
                player.hp = None
                if player.team is not None:
                    player.spawn()
            self.protocol.on_game_end()
        else:
            flag = self.team.other.set_flag()
            flag.update()

    def __del__(self):
        if self.player_id is None or self.player_id in self.protocol.players:
            return
        player_left.player_id = self.player_id
        self.protocol.send_contained(player_left, save = True)

def apply_script(protocol, connection, config):
    class InfiltrationConnection(connection):
        def on_team_join(self, team):
            attacker = self.protocol.attacker
            defender = self.protocol.defender
            attacker_count = attacker.count() + (1 if team is attacker else 0)
            defender_count = ((defender.count() + (1 if team is defender else 0))
                * ATTACKER_TO_DEFENDER_RATIO)
            attacker_count = attacker_count or ATTACKER_TO_DEFENDER_RATIO
            if ((attacker_count > defender_count and team is attacker) or
                (attacker_count < defender_count and team is defender)):
                self.send_chat(S_TEAM_FULL)
                return False
            return connection.on_team_join(self, team)

        def on_team_changed(self, old_team):
            if self.team and self.team.id in S_OBJECTIVES:
                self.send_chat(S_OBJECTIVES[self.team.id])
            connection.on_team_changed(self, old_team)

        def on_login(self, name):
            if self.team and self.team.id in S_OBJECTIVES:
                self.send_chat(S_OBJECTIVES[self.team.id])
            connection.on_login(self, name)

        def on_flag_capture(self):
            if ATTACKER_SCORE_MULTIPLIER > 1:
                dummy = DummyPlayer(self.protocol, self.team)
                self.protocol.attacker_dummy = dummy
                if self.protocol.attacker_dummy_calls is None:
                    self.protocol.attacker_dummy_calls = []
                for i in xrange(ATTACKER_SCORE_MULTIPLIER - 1):
                    delay = i * 0.1
                    dummy_call = callLater(delay,
                        self.protocol.attacker_dummy_score)
                    self.protocol.attacker_dummy_calls.append(dummy_call)
            self.protocol.cancel_defender_return_call()
            self.protocol.start_defender_score_loop()
            connection.on_flag_capture(self)

        def on_flag_take(self):
            if self.team is not self.protocol.attacker:
                return False
            if ON_FLAG_TAKE_FLASHES_FOG:
                self.protocol.fog_flash(self.team.color)
            if self.protocol.defender_score_loop.running:
                self.protocol.defender_score_loop.stop()
            return connection.on_flag_take(self)

        def on_flag_drop(self):
            self.protocol.start_defender_score_loop()
            connection.on_flag_drop(self)

    class InfiltrationProtocol(protocol):
        game_mode = CTF_MODE
        balanced_teams = None
        defender = None
        defender_score_loop = None
        defender_return_call = None
        attacker = None
        attacker_dummy = None
        attacker_dummy_calls = None

        def on_map_change(self, map):
            self.attacker = self.teams[ATTACKER_TEAM]
            self.defender = self.attacker.other
            self.defender_score_loop = LoopingCall(self.defender_score_cycle)
            self.start_defender_score_loop()
            protocol.on_map_change(self, map)

        def on_map_leave(self):
            if self.defender_score_loop and self.defender_score_loop.running:
                self.defender_score_loop.stop()
            self.defender_score_loop = None
            self.end_attacker_dummy_calls()
            protocol.on_map_leave(self)

        def on_game_end(self):
            self.end_attacker_dummy_calls()
            self.start_defender_score_loop()
            protocol.on_game_end(self)

        def on_flag_spawn(self, x, y, z, flag, entity_id):
            if flag.team is self.attacker:
                return 0, 0, 63
            return protocol.on_flag_spawn(self, x, y, z, flag, entity_id)

        def start_defender_score_loop(self):
            if self.defender_score_loop.running:
                self.defender_score_loop.stop()
            self.defender_score_loop.start(DEFENDER_SCORE_INTERVAL, now = False)

        def defender_score_cycle(self):
            dummy = DummyPlayer(self, self.defender)
            dummy.score()

        def attacker_dummy_score(self):
            self.attacker_dummy.score()
            if self.attacker_dummy is None:
                # this could happen if the dummy capture caused the game to end
                return
            self.attacker_dummy_calls.pop(0)
            if not self.attacker_dummy_calls:
                self.end_attacker_dummy_calls()

        def end_attacker_dummy_calls(self):
            if self.attacker_dummy_calls:
                for dummy_call in self.attacker_dummy_calls:
                    if dummy_call and dummy_call.active():
                        dummy_call.cancel()
            self.attacker_dummy_calls = None
            self.attacker_dummy = None

        def cancel_defender_return_call(self):
            if self.defender_return_call and self.defender_return_call.active():
                self.defender_return_call.cancel()
            self.defender_return_call = None

        def fog_flash(self, color):
            old_color = self.get_fog_color()
            self.set_fog_color(color)
            callLater(0.2, self.set_fog_color, old_color)

    return InfiltrationProtocol, InfiltrationConnection
