from pyspades.collision import vector_collision
from pyspades.constants import PICKAXE_TOOL
from twisted.internet.task import LoopingCall
import random

MELEE_DISTANCE = 2.0
UPDATE_FPS = 10

def apply_script(protocol, connection, config):
    melee_damage = config.get('melee_damage', 20)
    class MeleeProtocol(protocol):
        def __init__(self, *arg, **kw):
            protocol.__init__(self, *arg, **kw)
            self.melee_update = LoopingCall(self.update_melee)
            self.melee_update.start(1.0 / UPDATE_FPS)
            
        def update_melee(self):
            checked = set()
            for player1 in self.players.values():
                if player1 in checked or not player1.hp:
                    continue
                checked.add(player1)
                for player2 in self.players.values():
                    if player2 in checked or not player2.hp:
                        continue
                    fire_1 = (player1.tool == PICKAXE_TOOL and 
                        player1.world_object.fire)
                    fire_2 = (player2.tool == PICKAXE_TOOL and 
                        player2.world_object.fire)
                    if fire_1 and fire_2:
                        fire_1 = bool(random.randrange(2))
                        fire_2 = not fire_1
                    if fire_1:
                        attack_player = player1
                        other_player = player2
                    elif fire_2:
                        attack_player = player2
                        other_player = player1
                    else:
                        continue
                    if vector_collision(player1.world_object.position, 
                                        player2.world_object.position,
                                        MELEE_DISTANCE):
                        hit_amount = melee_damage
                        returned = attack_player.on_hit(hit_amount, 
                            other_player)
                        if returned == False:
                            continue
                        elif returned is not None:
                            hit_amount = returned
                        other_player.hit(hit_amount, attack_player)
                        checked.add(other_player)
    return MeleeProtocol, connection