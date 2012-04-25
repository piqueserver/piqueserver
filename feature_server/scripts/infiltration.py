"""
Attackers get ATTACKER_SCORE_MULTIPLIER points for taking and capturing
the intel.

Defenders gain 1 point every DEFENDER_SCORE_INTERVAL seconds the intel
is untouched.

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
FLAG_TAKE_FLASHES_FOG = True

S_TEAM_FULL = 'Team is full'
S_ATTACKER_DESC = 'ATTACKERS: Infiltrate the enemy base and steal the intel!'
S_DEFENDER_DESC = 'DEFENDERS: Hold your ground! Earn points by keeping the ' \
    'intel safe'
S_DESCS = {
    ATTACKER_TEAM : S_ATTACKER_DESC,
    (1 - ATTACKER_TEAM) : S_DEFENDER_DESC
}

class DummyPlayer():
    protocol = None
    team = None
    player_id = None
    
    def __init__(self, protocol, team):
        self.protocol = protocol
        self.team = team
        max_players = min(32, self.protocol.max_players)
        if len(protocol.connections) > max_players:
            try:
                self.player_id = next(self.team.get_players())
            except StopIteration:
                self.player_id = None
        else:
            self.player_id = protocol.player_ids.pop()
        if self.player_id is None:
            return
        create_player.x = 0
        create_player.y = 0
        create_player.z = 63
        create_player.weapon = RIFLE_WEAPON
        create_player.player_id = self.player_id
        create_player.name = team.name
        create_player.team = team.id
        protocol.send_contained(create_player)
    
    def score(self):
        if self.player_id is None or self.protocol.game_mode != CTF_MODE:
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
        self.protocol.send_contained(player_left)
        self.protocol.player_ids.put_back(self.player_id)

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
            if self.team and self.team.id in S_DESCS:
                self.send_chat(S_DESCS[self.team.id])
            connection.on_team_changed(self, old_team)
        
        def on_login(self, name):
            if self.team and self.team.id in S_DESCS:
                self.send_chat(S_DESCS[self.team.id])
            connection.on_login(self, name)
        
        def on_flag_capture(self):
            if ATTACKER_SCORE_MULTIPLIER > 1:
                dummy = DummyPlayer(self.protocol, self.team)
                for i in xrange(ATTACKER_SCORE_MULTIPLIER - 1):
                    dummy.score()
            self.protocol.start_defender_score_loop()
            connection.on_flag_capture(self)
        
        def on_flag_take(self):
            if self.team is self.protocol.defender:
                return False
            if FLAG_TAKE_FLASHES_FOG:
                self.protocol.fog_flash(self.team.color)
            self.protocol.defender_score_loop.stop()
            return connection.on_flag_take(self)
        
        def on_flag_drop(self):
            self.protocol.start_defender_score_loop()
            connection.on_flag_drop(self)
    
    class InfiltrationProtocol(protocol):
        game_mode = CTF_MODE
        attacker = None
        defender = None
        defender_score_loop = None
        balanced_teams = None
        
        def on_map_change(self, map):
            self.attacker = self.teams[ATTACKER_TEAM]
            self.defender = self.attacker.other
            self.defender_score_loop = LoopingCall(self.defender_score_cycle)
            self.start_defender_score_loop()
            protocol.on_map_change(self, map)
            print self.teams[0].color
        
        def on_map_leave(self):
            if self.defender_score_loop and self.defender_score_loop.running:
                self.defender_score_loop.stop()
            self.defender_score_loop = None
            protocol.on_map_leave(self)
        
        def start_defender_score_loop(self):
            self.defender_score_loop.start(DEFENDER_SCORE_INTERVAL, now = False)
        
        def defender_score_cycle(self):
            dummy = DummyPlayer(self, self.defender)
            dummy.score()
       
        def fog_flash(self, color):
            old_color = self.get_fog_color()
            self.set_fog_color(color)
            callLater(0.2, self.set_fog_color, old_color)
        
        def on_flag_spawn(self, x, y, z, flag, entity_id):
            if flag.team is self.attacker:
                return 0, 0, 63
            return protocol.on_flag_spawn(self, x, y, z, flag, entity_id)
    
    return InfiltrationProtocol, InfiltrationConnection