import math
import time
import heapq
import asyncio

from pyspades import world
from pyspades.constants import *
from pyspades import contained as loaders
from piqueserver.commands import command
from pyspades.common import Vertex3
from piqueserver.config import config as cfg


@command('bots', admin_only=False)
def bots(connection):
    while len(connection.protocol.players) < 30:
        player = connection.protocol.create_bot()
        #player.set_location(connection.protocol.players[0].world_object.position.get())

draw = True
@command('t', admin_only=False)
def test(connection):
    for player in list(connection.protocol.players.values()):
        if player.bot:
            asyncio.get_event_loop().create_task(player.bot_go(connection.protocol.players[0].world_object.position))
            '''
            pos = player.world_object.position
            target = connection.protocol.players[0].world_object.position
            lag = time.monotonic()
            res = player.protocol.map.a_star(pos.x, pos.y, pos.z, target.x, target.y, target.z)
            print(time.monotonic() - lag)
            for p in res:
                player.protocol.build_block(p[0], p[1], p[2]+3)
            '''

def xyz(x: int, y: int, z: int) -> int:
    return x + y*512 + z*512*512

def check_road2(solid, x1: int, y1: int, z1: int, x2: int, y2: int, z2: int) -> float:
    # Не даём выйти за границу карты
    if x2 >= 512 or x2 < 0 or y2 >= 512 or y2 < 0 or z2 >= 64 or z2 < 0:
        return -1
    if not travelable[xyz(x2, y2, z2)] or not travelable[xyz(x1, y1, z1)]:
        return -1
    # TODO Переписать логику на более интуитивно понятную
    # Проверка основания - наличие блока под ногами
    if travelable[xyz(x1, y1, z1 + 1)] or travelable[xyz(x2, y2, z2 + 1)]:
        return -1
    if x1 == x2 and y1 == y2 and z1 == z2:
        return 0
    if abs(x1-x2) > 1 or abs(y1-y2) > 1 or abs(z1-z2) > 1:
        return -1
    if x1 != x2 and y1 != y2:
        #if not solid(x1, y2, z2) or not solid(x2, y1, z2):
        # TODO здесь что-то не так с диагональным блоком на другой высоте
        # При движении по диагонали оба боковых столба должны быть свбодны
        if not travelable[xyz(x1, y2, z2)] or not travelable[xyz(x2, y1, z2)]:
            return -1
        # Но хотя бы у одного должно быть основание
        if travelable[xyz(x1, y2, z2 + 1)] and travelable[xyz(x2, y1, z2 + 1)]:
            return -1
        return 1.732 if z1 != z2 else 1.414
    else:
        return 1.414 if z1 != z2 else 1

class BotInfo:
    target = Vertex3(0, 0, 0)
    attacking = False
    next_pos = None
    prev_pos = None
    stuck = 0
    task = None
    loop = None
    path = []

def apply_script(protocol, connection, config):

    class BotsConnection(connection):
        bot = None
        '''
        def on_team_join(self, team: 'FeatureTeam'):
            if self.bot:
                return self.protocol.green_team
            else:
                return self.protocol.blue_team
        '''

        def simulate_input(self, up=False, down=False, left=False, 
        right=False, jump=False, crouch=False, sneak=False, sprint=False):
            packet = loaders.InputData()
            packet.up = up
            packet.down = down
            packet.left = left
            packet.right = right
            packet.jump = jump
            packet.crouch = crouch
            packet.sneak = sneak
            packet.sprint = sprint
            packet.player_id = self.player_id
            self.on_input_data_recieved(packet)

        def simulate_weapon_input(self, primary=True, secondary=False):
            packet = loaders.WeaponInput()
            packet.primary = primary
            packet.secondary = secondary
            packet.player_id = self.player_id
            self.on_weapon_input_recieved(packet)

        def simulate_hit(self, player):
            packet = loaders.HitPacket()
            packet.value = MELEE # TORSO, HEAD, ARMS, LEGS, MELEE
            packet.player_id = player.player_id
            self.on_hit_recieved(packet)

        def simulate_tool_change(self, tool=0):
            packet = loaders.SetTool()
            packet.value = tool
            packet.player_id = self.player_id
            self.on_tool_change_recieved(packet)

        def on_floor(self):
            if abs(self.world_object.velocity.z) > 0.0005:
                return False
            pos = self.world_object.position
            return self.protocol.map.get_solid(pos.x, pos.y, pos.z + 3)

        async def bot_go(self, target):
            self.bot_reset()
            while not self.on_floor():
                await asyncio.sleep(1/60)
            self.bot.target.x = int(target.x)
            self.bot.target.y = int(target.y)
            self.bot.target.z = int(target.z)
            pos = self.world_object.position
            self.bot.path = self.protocol.map.a_star(int(pos.x), int(pos.y), int(pos.z),
                int(target.x), int(target.y), int(target.z), False, False)


        def bot_loop(self):
            if self.tool != SPADE_TOOL:
                self.simulate_tool_change(SPADE_TOOL)
            # unstuck
            if self.bot.stuck > 2:
                self.bot_reset()
                self.bot.stuck = 0
                print("UNSTUCKED")
            self.bot.stuck += 1

            pos = self.protocol.players[0].world_object.position.copy()
            self.bot.target = self.protocol.players[0]
            if (not self.bot.task) or (self.bot.task.done()) or (self.bot.task.cancelled()):
                self.bot.task = asyncio.get_event_loop().create_task(a_star(self, pos))
            dist = self.world_object.position.distance(pos)
            self.bot.loop = asyncio.get_event_loop().call_later(min(0.3 + dist/8, 5), self.bot_loop)


        def bot_reset(self):
            self.simulate_input()
            self.world_object.velocity.zero()
            self.set_location_safe(self.world_object.position.get())
            self.bot.path.clear()
            self.bot.next_pos = None
            self.bot.prev_pos = None
            if self.bot.task:
                self.bot.task.cancel()
    
    class BotsProtocol(protocol):

        def create_bot(self, team_id=0, weapon_id=0, name="bot"):
            player = BotsConnection(self, self.host)
            player.disconnected = True
            player.local = True
            player.bot = BotInfo()
            player.player_id = self.player_ids.pop()
            
            packet = loaders.ExistingPlayer()
            packet.player_id = player.player_id
            packet.team = team_id
            packet.weapon = weapon_id
            packet.name = name
            connection.on_new_player_recieved(player, packet)
            #asyncio.get_event_loop().call_later(0.5, player.bot_loop)
            return player

        def remove_bot(self, player):
            player.drop_flag()
            player_left = loaders.PlayerLeft()
            player_left.player_id = player.player_id
            self.send_contained(player_left, save=True)
            self.players.pop(player.player_id)
            self.player_ids.put_back(player.player_id)
            player.reset()

        def on_map_leave(self):
            for player in list(self.players.values()):
                if player.bot:
                    player.bot_reset()
                    player.bot.loop.cancel()
                    self.remove_bot(player)
            protocol.on_map_leave(self)

        def on_world_update(self):
            for player in self.players.values():
                if player.bot:
                    pos = player.world_object.position
                    vel = player.world_object.velocity
                    if (player.bot.next_pos is None) and player.bot.path and player.on_floor():
                        player.bot.stuck = 0
                        player.bot.next_pos = Vertex3(*player.bot.path.pop(0))
                        player.bot.next_pos.x += 0.5
                        player.bot.next_pos.y += 0.5
                        player.bot.next_pos.z += 0.748 # Head offset
                        #print('==========')
                        if player.bot.prev_pos is None:
                            player.bot.prev_pos = player.bot.next_pos
                        #cost = check_road(player, player.bot.prev_pos, player.bot.next_pos, tmp=False)
                        cost = 1
                        #print(player.name+" "+str(cost))
                        if cost > 1.8:
                            player.simulate_input(up=True, sprint=True)
                        elif cost >= 0:
                            player.simulate_input(up=True, sprint=False)
                        else:
                            print("INVALIDE PATH")
                            print(player.bot.prev_pos)
                            print(player.bot.next_pos)
                            player.simulate_input()
                            player.world_object.velocity.zero()
                            player.bot.path.clear()
                            player.bot.next_pos = None
                            player.bot.prev_pos = None
                            player.bot.task.cancel()
                            player.bot.loop.cancel()
                            #player.bot_reset()

                    if player.bot.next_pos is not None:
                        npos = player.bot.next_pos
                        old = player.world_object.orientation
                        new = (npos-pos)
                        new.normalize()
                        new.z = min(new.z, 0.5)
                        new.normalize()
                        if player.on_floor():
                            vel.set(*(new*vel.length()).get())
                        player.world_object.set_orientation(*new.get())

                        # Сalculate angle of rotation
                        #dot = old.x*new.x + old.y*new.y #+ old.z*new.z
                        #if dot > 1:
                        #    dot = 1
                        #if dot < -1:
                        #    dot = -1
                        #angle = math.acos(dot)
                        #angle = math.degrees(angle)
                        #angle = math.atan2(old.y, old.x) - math.atan2(new.y, new.x)
                        #while angle > math.pi:
                        #    angle -= math.pi
                        #while angle <= -math.pi:
                        #    angle += math.pi
                        #angle = abs(math.degrees(angle))
                        #if angle > 35:
                        #    vel.set(0, 0, 0)
                        #    print(angle)

                        if abs(pos.x-npos.x) < 0.17 and abs(pos.y-npos.y) < 0.17 and abs(pos.z-npos.z) <= 1:
                            # Телепортировать точно в центр, если движение было в одной плоскости
                            # Нужно для точного прохождения узких мест, чтобы не цеплялся за углы
                            #if npos.y == player.bot.prev_pos.y:
                            player.world_object.set_position(npos.x, npos.y, pos.z)
                            player.bot.prev_pos = player.bot.next_pos
                            player.bot.next_pos = None
                            if not player.bot.path:
                                player.simulate_input()
                                vel.zero()
                        '''
                        if pos.distance(player.bot.target.world_object.position) <= MELEE_DISTANCE:
                            if not player.bot.attacking:
                                player.simulate_weapon_input()
                                player.bot.attacking = True
                            player.simulate_hit(player.bot.target)
                        elif player.bot.attacking:
                            player.simulate_weapon_input(False)
                            player.bot.attacking = False
                        '''

            return protocol.on_world_update(self)

    return BotsProtocol, BotsConnection