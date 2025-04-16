"""
Tug of War game mode, where you must progressively capture the enemy CPs in a
straight line to win.

Maintainer: mat^2
"""

import random
import math
from pyspades.constants import TC_MODE
from pyspades.server import Territory

# Procedural generation parameters for when capture points are not specified in map.txt files
CP_COUNT = 6 # Number of capture points. Must be at least 2
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

        def get_cp(self, entities, index):
            if index < 0:
                return self.blue_team.last_spawn
            elif index > len(entities) - 1:
                return self.green_team.last_spawn
            return entities[index]
        
        def update_cps(self, entities):
            prev = None
            for i, curr in enumerate(entities):
                if prev is not None:
                    if prev.team is not None and prev.team.id == self.blue_team.id and curr.team is not None and curr.team.id == self.green_team.id:
                        # Blue -> Green
                        self.blue_team.cp  = curr
                        self.green_team.cp = prev
                        self.blue_team.spawn_cp  = self.get_cp(entities, i - 2)
                        self.green_team.spawn_cp = self.get_cp(entities, i + 1)
                        curr.disabled = False
                        prev.disabled = False
                    elif prev.team is not None and prev.team.id == self.blue_team.id and curr.team == None:
                        # Blue -> Neutral
                        self.blue_team.cp  = curr
                        self.green_team.cp = curr
                        self.blue_team.spawn_cp  = self.get_cp(entities, i - 2)
                        self.green_team.spawn_cp = self.get_cp(entities, i + 1)
                        curr.disabled = False
                    else: # Disable all other capture points.
                        curr.disabled = True
                else: # Disable all other capture points.
                    curr.disabled = True
                prev = curr
        
        def get_cp_entities(self):
            extensions = self.map_info.extensions
            map = self.map

            # num_cps is the number of actual capturable points
            # num_extra cps includes an extra 'spawn' cp, which is where players will spawn when they only have one capture point left as their color
            # Players will spawn at the second closest capture point to the other side
            num_cps = CP_COUNT
            num_extra_cps = num_cps + 2
            center = (num_extra_cps - 1) / 2

            # The (x,y) positions of all capture points, plus two extra for spawn cps
            # First blue cp and last green cp are spawn cps
            cp_positions = []

            # First, get the (x,y) positions of capture points
            if "tow_locations" in extensions: # Get from map extensions if specified
                cp_positions = extensions["tow_locations"]

                num_extra_cps = len(cp_positions)
                num_cps = num_extra_cps - 2
                center = (num_extra_cps - 1) / 2
            else: # Otherwise, generate a random curve
                magnitude = 10
                angle = random.uniform(START_ANGLE, END_ANGLE)
                x, y = (0, random.randrange(64, 512 - 64))

                square_1 = range(128)
                square_2 = range(512 - 128, 512)

                points = []

                # Generate points along a curve
                while True:
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
                
                move = 512 / num_extra_cps
                offset = move / 2
                
                # Take `num_extra_cps` evenly spaced points from that curve for our real positions
                for i in range(num_extra_cps):
                    index = 0
                    while True:
                        p_x, p_y = points[index]
                        index += 1
                        if p_x >= offset:
                            break
                    cp_positions.append(((p_x, p_y)))
                    offset += move

            # Create entities based on the positions we generated/loaded from map extensions
            entities = [] # Does not include extra spawn CPs
            entity_index = 0
            
            for i, (x, y) in enumerate(cp_positions):
                entity = TugTerritory(entity_index, self, *(x, y, map.get_z(x, y)))
                
                if i == 0: # Blue extra spawn
                    entity.id = -1
                    self.blue_team.last_spawn = entity
                    continue # Must not add extra spawns to entities list
                elif i == len(cp_positions) - 1: # Green extra spawn
                    self.green_team.last_spawn = entity
                    continue # Must not add extra spawns to entities list
                elif i < center: # Blue
                    entity.team = self.blue_team
                elif i > center: #Green
                    entity.team = self.green_team
                else: # Neutral
                    entity.team = None
                entities.append(entity)
                entity_index += 1

            self.update_cps(entities)
            return entities
        def on_cp_capture(self, territory):
            self.update_cps(self.entities)

    return TugProtocol, TugConnection
