from pyspades.constants import *
from pyspades.server import Territory
import random

CP_COUNT = 8
CP_EXTRA_COUNT = CP_COUNT + 2 # PLUS last 'spawn'

def limit(value):
    return min(512, max(0, value))

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

def get_index(value):
    if value < 0:
        raise IndexError()
    return value

def apply_script(protocol, connection, config):
    class TugConnection(connection):
        def get_spawn_location(self):
            if self.team.spawn_cp is None:
                base = self.team.last_spawn
            else:
                base = self.team.spawn_cp
            return base.get_spawn_location()
            
    class TugProtocol(protocol):
        game_mode = TC_MODE
        
        def get_cp_entities(self):
            # generate positions
            
            blue_cp = []
            green_cp = []

            move = 512 / CP_EXTRA_COUNT
            x = -move / 2
            y = self.get_random_location(
                zone = (move, 0, move * 2, 512))[1]
            for i in xrange(CP_EXTRA_COUNT / 2):
                x += move
                blue_cp.append((x, y))
                y = self.get_random_location(
                    zone = (x, limit(y - 64), x + move, limit(y + 64)))[1]

            for i in xrange(CP_EXTRA_COUNT / 2):
                x += move
                green_cp.append((x, y))
                y = self.get_random_location(
                    zone = (x, limit(y - 64), x + move, limit(y + 64)))[1]
            index = 0
            entities = []
            map = self.map
            
            # make entities
            
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
                    entity.id = index + 1
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
            for team in self.teams:
                try:
                    old_cp = team.cp
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