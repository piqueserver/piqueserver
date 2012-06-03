"""
Airstrikes. Boom!

Maintainer: mat^2 / hompy
"""

from math import ceil
from random import randrange, uniform
from twisted.internet.reactor import callLater, seconds
from pyspades.server import orientation_data, grenade_packet
from pyspades.common import coordinates, to_coordinates, Vertex3
from pyspades.collision import distance_3d_vector
from pyspades.world import Grenade
from pyspades.constants import UPDATE_FREQUENCY
from commands import alias, add

SCORE_REQUIREMENT = 0
STREAK_REQUIREMENT = 8
TEAM_COOLDOWN = 25.0
REFILL_ON_AIRSTRIKE = True # set to False if you don't want to be healed

S_READY = 'Airstrike support ready! Launch with e.g. /airstrike B4'
S_NO_SCORE = 'You need a total score of {score} (kills or intel) to ' \
    'unlock airstrikes!'
S_NO_STREAK = 'Every {streak} consecutive kills (without dying) you get an ' \
    'airstrike. {remaining} kills to go!'
S_BAD_COORDS = "Bad coordinates: should be like 'A4', 'G5'. Look them up in the map"
S_COOLDOWN = '{seconds} seconds before your team can launch another airstrike'
S_ALLIED = 'Ally {player} called in an airstrike on location {coords}'
S_ENEMY = '[WARNING] Enemy air support heading to {coords}!'
S_UNLOCKED = 'You have unlocked airstrike support!'
S_UNLOCKED_TIP = 'Each {streak}-kill streak will clear you for one airstrike'

@alias('a')
def airstrike(connection, coords = None):
    protocol = connection.protocol
    if connection not in protocol.players:
        raise ValueError()
    player = connection
    if not coords and player.airstrike:
        return S_READY
    if player.kills < SCORE_REQUIREMENT:
        return S_NO_SCORE.format(score = SCORE_REQUIREMENT)
    elif not player.airstrike:
        kills_left = STREAK_REQUIREMENT - (player.streak % STREAK_REQUIREMENT)
        return S_NO_STREAK.format(streak = STREAK_REQUIREMENT,
            remaining = kills_left)
    try:
        coord_x, coord_y = coordinates(coords)
    except (ValueError):
        return S_BAD_COORDS
    last_airstrike = getattr(player.team, 'last_airstrike', None)
    if last_airstrike and seconds() - last_airstrike < TEAM_COOLDOWN:
        remaining = TEAM_COOLDOWN - (seconds() - last_airstrike)
        return S_COOLDOWN.format(seconds = int(ceil(remaining)))
    player.start_airstrike(coord_x, coord_y)

add(airstrike)

def apply_script(protocol, connection, config):
    class AirstrikeConnection(connection):
        airstrike = False
        airstrike_grenade_calls = None
        last_streak = None
        
        def start_airstrike(self, coord_x, coord_y):
            coords = to_coordinates(coord_x, coord_y)
            message = S_ALLIED.format(player = self.name, coords = coords)
            self.protocol.send_chat(message, global_message = False,
                team = self.team)
            message = S_ENEMY.format(coords = coords)
            self.protocol.send_chat(message, global_message = False,
                team = self.team.other)
            
            self.team.last_airstrike = seconds()
            self.airstrike = False
            callLater(2.5, self.do_airstrike, coord_x, coord_y)
        
        def do_airstrike(self, coord_x, coord_y):
            if self.name is None:
                return
            self.airstrike_grenade_calls = []
            going_right = self.team.id == 0
            coord_x += -64 if going_right else 64
            coord_x = max(0, min(511, coord_x))
            min_spread = 4.0 if going_right else -5.0
            max_spread = 5.0 if going_right else -4.0
            worst_delay = 0.0
            z = 1
            for i in xrange(12):
                x = coord_x + randrange(64)
                y = coord_y + randrange(64)
                for j in xrange(5):
                    x += uniform(min_spread, max_spread)
                    delay = i * 0.9 + j * 0.14
                    worst_delay = max(delay, worst_delay)
                    call = callLater(delay, self.create_airstrike_grenade,
                        x, y, z)
                    self.airstrike_grenade_calls.append(call)
        
        def end_airstrike(self):
            if self.airstrike_grenade_calls:
                for grenade_call in self.airstrike_grenade_calls:
                    if grenade_call and grenade_call.active():
                        grenade_call.cancel()
            self.airstrike_grenade_calls = None
        
        def on_team_changed(self, old_team):
            self.end_airstrike()
            connection.on_team_changed(self, old_team)
        
        def on_reset(self):
            self.end_airstrike()
            self.last_streak = None
            connection.on_reset(self)
        
        def on_kill(self, killer, type, grenade):
            self.airstrike = False
            self.last_streak = None
            connection.on_kill(self, killer, type, grenade)
        
        def create_airstrike_grenade(self, x, y, z):
            going_right = self.team.id == 0
            position = Vertex3(x, y, z)
            velocity = Vertex3(1.0 if going_right else -1.0, 0.0, 0.5)
            grenade = self.protocol.world.create_object(Grenade, 0.0,
                position, None, velocity, self.airstrike_exploded)
            grenade.name = 'airstrike'
            estimate_travel = 61 if going_right else -61
            eta = self.protocol.map.get_height(x + estimate_travel, y) * 0.033
            collision = grenade.get_next_collision(UPDATE_FREQUENCY)
            if collision:
                eta, x, y, z = collision
            grenade.fuse = eta
            grenade_packet.value = grenade.fuse
            grenade_packet.player_id = self.player_id
            grenade_packet.position = position.get()
            grenade_packet.velocity = velocity.get()
            self.protocol.send_contained(grenade_packet)
        
        def airstrike_exploded(self, grenade):
            pos, vel = grenade.position, grenade.velocity
            vel.normalize()
            extra_distance = 3
            while extra_distance:
                extra_distance -= 1
                pos += vel
                solid = self.protocol.map.get_solid(*pos.get())
                if solid or solid is None:
                    break
            self.grenade_exploded(grenade)
        
        def add_score(self, score):
            connection.add_score(self, score)
            score_met = (self.kills >= SCORE_REQUIREMENT)
            streak_met = (self.streak >= STREAK_REQUIREMENT)
            if not score_met:
                return
            just_unlocked = False
            if self.kills - score < SCORE_REQUIREMENT:
                self.send_chat(S_UNLOCKED)
                self.send_chat(S_UNLOCKED_TIP.format(streak = STREAK_REQUIREMENT))
                just_unlocked = True
            if not streak_met:
                return
            if ((self.streak % STREAK_REQUIREMENT == 0 or just_unlocked) and
                self.streak != self.last_streak):
                self.send_chat(S_READY)
                self.airstrike = True
                self.last_streak = self.streak
                if REFILL_ON_AIRSTRIKE:
                    self.refill()
    
    return protocol, AirstrikeConnection