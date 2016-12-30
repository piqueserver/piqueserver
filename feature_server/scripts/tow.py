"""
Tug of War game mode, where you must progressively capture the enemy CPs in a
straight line to win.

Maintainer: mat^2
"""

from pyspades.constants import *
from pyspades.server import Territory
import random
import math
from math import pi

CP_COUNT = 6
CP_EXTRA_COUNT = CP_COUNT + 2 # PLUS last 'spawn'
ANGLE = 65
START_ANGLE = math.radians(-ANGLE)
END_ANGLE = math.radians(ANGLE)
DELTA_ANGLE = math.radians(30)
FIX_ANGLE = math.radians(4)

HELP = [
    "In Tug of War, you capture your opponents' front CP to advance."
]

class TugTerritory(Territory):
    disabled = True

    def add_player(self, player):
        if self.disabled:
            return
        Territory.add_player(self, player)

    def enable(self):
        self.disabled = False

    def disable(self):
        for player in self.players.copy():
            self.remove_player(player)
        self.disabled = True
        self.progress = float(self.team.id)

def get_index(value):
    if value < 0:
        raise IndexError()
    return value

def random_up_down(value):
    value /= 2
    return random.uniform(-value, value)

def limit_angle(value):
    return min(END_ANGLE, max(START_ANGLE, value))

def limit_dimension(value):
    return min(511, max(0, value))

def get_point(x, y, magnitude, angle):
    return (limit_dimension(x + math.cos(angle) * magnitude),
            limit_dimension(y + math.sin(angle) * magnitude))

def apply_script(protocol, connection, config):
    class TugConnection(connection):
        def get_spawn_location(self):
            if self.team.spawn_cp is None:
                base = self.team.last_spawn
            else:
                base = self.team.spawn_cp
            return base.get_spawn_location()

        def on_spawn(self, pos):
            for line in HELP:
                self.send_chat(line)
            return connection.on_spawn(self, pos)

    class TugProtocol(protocol):
        game_mode = TC_MODE

        def get_cp_entities(self):
            # generate positions

            map = self.map
            blue_cp = []
            green_cp = []

            magnitude = 10
            angle = random.uniform(START_ANGLE, END_ANGLE)
            x, y = (0, random.randrange(64, 512 - 64))

            points = []

            square_1 = xrange(128)
            square_2 = xrange(512 - 128, 512)

            while 1:
                top = int(y) in square_1
                bottom = int(y) in square_2
                if top:
                    angle = limit_angle(angle + FIX_ANGLE)
                elif bottom:
                    angle = limit_angle(angle - FIX_ANGLE)
                else:
                    angle = limit_angle(angle + random_up_down(DELTA_ANGLE))
                magnitude += random_up_down(2)
                magnitude = min(15, max(5, magnitude))
                x2, y2 = get_point(x, y, magnitude, angle)
                if x2 >= 511:
                    break
                x, y = x2, y2
                points.append((int(x), int(y)))

            move = 512 / CP_EXTRA_COUNT
            offset = move / 2

            for i in xrange(CP_EXTRA_COUNT):
                index = 0
                while 1:
                    p_x, p_y = points[index]
                    index += 1
                    if p_x >= offset:
                        break
                if i < CP_EXTRA_COUNT / 2:
                    blue_cp.append((p_x, p_y))
                else:
                    green_cp.append((p_x, p_y))
                offset += move

            # make entities

            index = 0
            entities = []

            for i, (x, y) in enumerate(blue_cp):
                entity = TugTerritory(index, self, *(x, y, map.get_z(x, y)))
                entity.team = self.blue_team
                if i == 0:
                    self.blue_team.last_spawn = entity
                    entity.id = -1
                else:
                    entities.append(entity)
                    index += 1

            self.blue_team.cp = entities[-1]
            self.blue_team.cp.disabled = False
            self.blue_team.spawn_cp = entities[-2]

            for i, (x, y) in enumerate(green_cp):
                entity = TugTerritory(index, self, *(x, y, map.get_z(x, y)))
                entity.team = self.green_team
                if i == len(green_cp) - 1:
                    self.green_team.last_spawn = entity
                    entity.id = index
                else:
                    entities.append(entity)
                    index += 1

            self.green_team.cp = entities[-CP_COUNT/2]
            self.green_team.cp.disabled = False
            self.green_team.spawn_cp = entities[-CP_COUNT/2 + 1]

            return entities

        def on_cp_capture(self, territory):
            team = territory.team
            if team.id:
                move = -1
            else:
                move = 1
            for team in [self.blue_team, self.green_team]:
                try:
                    team.cp = self.entities[get_index(team.cp.id + move)]
                    team.cp.enable()
                except IndexError:
                    pass
                try:
                    team.spawn_cp = self.entities[get_index(
                        team.spawn_cp.id + move)]
                except IndexError:
                    team.spawn_cp = team.last_spawn
            cp = (self.blue_team.cp, self.green_team.cp)
            for entity in self.entities:
                if not entity.disabled and entity not in cp:
                    entity.disable()

    return TugProtocol, TugConnection
