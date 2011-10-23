from pyspades.constants import *
from pyspades.server import Territory

CP_COUNT = 6

BLUE_CP = []
GREEN_CP = []

move = 512 / (CP_COUNT + 1)
x = 0
for _ in xrange(CP_COUNT / 2):
    x += move
    BLUE_CP.append((x, 512 / 2))

for _ in xrange(CP_COUNT / 2):
    x += move
    GREEN_CP.append((x, 512 / 2))

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
            return self.team.spawn_cp.get_spawn_location()
            
    class TugProtocol(protocol):
        game_mode = TC_MODE
        
        def get_cp_entities(self):
            index = 0
            entities = []
            map = self.map
            
            for x, y in BLUE_CP:
                entity = TugTerritory(index, self, *(x, y, map.get_z(x, y)))
                entity.team = self.blue_team
                entities.append(entity)
                index += 1
            
            self.blue_team.cp = entities[-1]
            self.blue_team.cp.disabled = False
            self.blue_team.spawn_cp = entities[-2]
                
            for x, y in GREEN_CP:
                entity = TugTerritory(index, self, *(x, y, map.get_z(x, y)))
                entity.team = self.green_team
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
                    pass
            cp = (self.blue_team.cp, self.green_team.cp)
            for entity in self.entities:
                if not entity.disabled and entity not in cp:
                    entity.disable()

    return TugProtocol, TugConnection