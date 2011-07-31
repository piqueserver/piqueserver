from pyspades.collision import vector_collision
from pyspades.constants import DAGGER_TOOL

MELEE_DISTANCE = 2.0

def apply_script(protocol, connection, config):
    class MeleeProtocol(protocol):
        def on_world_update(self):
            checked = set()
            for player1 in self.players.values():
                if player1 in checked or not player1.hp:
                    continue
                checked.add(player1)
                for player2 in self.players.values():
                    if player2 in checked or not player2.hp:
                        continue
                    if player1.tool == DAGGER_TOOL and player1.world_object.fire:
                        attack_player = player1
                        other_player = player2
                    elif player2.tool == DAGGER_TOOL and player2.world_object.fire:
                        attack_player = player2
                        other_player = player1
                    else:
                        continue
                    if vector_collision(player1.world_object.position, 
                                        player2.world_object.position,
                                        MELEE_DISTANCE):
                        other_player.hit(100, attack_player)
                        checked.add(other_player)
    return MeleeProtocol, connection