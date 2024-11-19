import math
import time
import heapq
import asyncio
from typing import *
from multiprocessing import Process, Manager, Value
from twisted.internet import reactor

from pyspades import world
from pyspades.constants import *
from pyspades import contained as loaders
from piqueserver.commands import command
from pyspades.common import Vertex3
from piqueserver.config import config as cfg


def check_straight_road(player, p1, p2) -> int:
    if int(p1.z) != int(p2.z):
        return -1
    solid = player.protocol.map.get_solid
    x1 = int(p1.x) + 0.5
    y1 = int(p1.y) + 0.5
    x2 = int(p2.x) + 0.5
    y2 = int(p2.y) + 0.5
    z = int(p1.z)

    x, y = x1, y1
    len_x = x2 - x1
    len_y = y2 - y1
    max_len = int(max(abs(len_x), abs(len_y))) * 3
    if not max_len:
        return 0
    dx = len_x / max_len
    dy = len_y / max_len

    for i in range(0, max_len):
        if (solid(x, y, z + 0) or solid(x, y, z + 1) or solid(x, y, z + 2) or
            solid(x+0.49, y+0.49, z) or solid(x+0.49, y+0.49, z + 1) or solid(x+0.49, y+0.49, z + 2) or
            solid(x-0.49, y+0.49, z) or solid(x-0.49, y+0.49, z + 1) or solid(x-0.49, y+0.49, z + 2) or
            solid(x+0.49, y-0.49, z) or solid(x+0.49, y-0.49, z + 1) or solid(x+0.49, y-0.49, z + 2) or
            solid(x-0.49, y-0.49, z) or solid(x-0.49, y-0.49, z + 1) or solid(x-0.49, y-0.49, z + 2)):
            return -1
        # Хотя бы один блок должен быть под ногами
        if not(solid(x+0.49, y+0.49, z+3) or solid(x-0.49, y+0.49, z + 3) or solid(x+0.49, y-0.49, z + 3) or
            solid(x-0.49, y-0.49, z + 3)):
            return -1
        x += dx
        y += dy
    return p1.distance(p2)


def check_road(player, p1, p2):
    z1 = int(p1.z)
    z2 = int(p2.z)
    if z1 == z2:
        return check_straight_road(player, p1, p2)
    solid = player.protocol.map.get_solid
    def solid3(x, y ,z):
        return not(solid(x, y, z) or solid(x, y, z + 1) or solid(x, y, z + 2))
    x1 = int(p1.x) + 0.5
    y1 = int(p1.y) + 0.5
    x2 = int(p2.x) + 0.5
    y2 = int(p2.y) + 0.5
    z = min(z1, z2)
    if not solid3(x1, y1, z1) or not solid3(x2, y2, z2):
        return -1
    if x1 != x2 and y1 != y2:
        if not solid3(x1, y2, z) or not solid3(x2, y1, z):
            return -1
    if p1.distance(p2) > 1.8:
        return -1
    return p1.distance(p2)


def cut_straight_lines(player, path):
    if len(path) < 3:
        return path
    p1 = path[0]
    res = []
    lp = p1
    for p in path:
        if not check_road(player, Vertex3(*p1), Vertex3(*p)):
            res.append(lp)
            p1 = lp
        lp = p
    res.append(lp)
    return res

class BotInfo:
    def __init__(self):
        self.target_player = None
        self.target_pos = Vertex3(0, 0, 0)
        self.active = False
        self.next_pos = None
        self.prev_pos = None
        self.stuck = 0
        self.stuck_cup: int = 2
        self.task = None
        self.path: List[Tuple[int, int, int]] = []

def apply_script(protocol, connection, config):

    class BotCoreConnection(connection):
        def __init__(self, *arg, **kw):
            self.bot: Optional[BotInfo] = None
            connection.__init__(self, *arg, **kw)

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
            if self.world_object.primary_fire == primary:
                if self.world_object.secondary_fire == secondary:
                    return
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
            if self.tool == tool:
                return
            packet = loaders.SetTool()
            packet.value = tool
            packet.player_id = self.player_id
            self.on_tool_change_recieved(packet)

        def check_floor(self):
            if abs(self.world_object.velocity.z) > 0.005:
                return False
            pos = self.world_object.position
            return self.protocol.map.get_solid(pos.x, pos.y, pos.z + 3)

        async def bot_pathfind(self):
            while not self.check_floor():
                await asyncio.sleep(1/60)
            pos = self.world_object.position.copy()
            pos.x = int(pos.x)
            pos.y = int(pos.y)
            pos.z = int(pos.z)
            target = self.bot.target_pos
            path = self.bot.path
            # Reuse old calculation
            '''
            if path:
                best_i = -1
                best_score = 9999999
                all_cost = 0
                if self.bot.next_pos is None:
                    prev_pos = pos
                else:
                    prev_pos = self.bot.next_pos
                for i in range(0, len(path)):
                    p = Vertex3(path[i][0], path[i][1], path[i][2])
                    cost = check_road(self, prev_pos, p)
                    if cost == -1:
                        #print(prev_pos)
                        #print(p)
                        break
                    all_cost += cost
                    dist = p.distance(target)
                    if dist*4 + all_cost <= best_score:
                        best_score = dist*4 + all_cost
                        best_i = i
                    prev_pos = p
                #print(str(best_i+1)+" / "+str(len(path)))
                if best_i >= 0:
                    pos = Vertex3(path[best_i][0], path[best_i][1], path[best_i][2])
                self.bot.path = path[0:best_i+1]
            '''
            self.bot.path.clear()
            await asyncio.sleep(0)
            final_distance = pos.distance(target)
            if final_distance < 10 and len(path) > 8:
                return
            if final_distance > 1.5:
                start = time.monotonic()
                future = self.protocol.map.a_star_start(int(pos.x), int(pos.y), int(pos.z),
                    int(target.x), int(target.y), int(target.z), False, False)
                while not future.ready():
                    await asyncio.sleep(0.001)
                self.bot.path.extend(future.get())
                self.bot.prev_pos = None
                self.bot.next_pos = None
                #print("END", self.name, int((time.monotonic() - start)*1000))

        def bot_step(self):
            pos = self.world_object.position
            vel = self.world_object.velocity
            if (self.bot.next_pos is None) and self.bot.path and self.check_floor():
                self.bot.stuck = 0
                self.bot.next_pos = Vertex3(*self.bot.path.pop(0))
                self.bot.next_pos.x += 0.5
                self.bot.next_pos.y += 0.5
                self.bot.next_pos.z += 0.748 # Head offset
                if self.bot.prev_pos is not None:
                    '''
                    while self.bot.path and check_straight_road(self, self.bot.prev_pos, Vertex3(*self.bot.path[0])) > 0:
                        self.bot.next_pos = Vertex3(*self.bot.path.pop(0))
                        self.bot.next_pos.x += 0.5
                        self.bot.next_pos.y += 0.5
                        self.bot.next_pos.z += 0.748 # Head offset
                    '''
                    self.bot.stuck_cup = self.bot.prev_pos.distance(self.bot.next_pos) / 2
                #self.protocol.build_block(*self.bot.next_pos.get())
                #print('==========')
                if self.bot.prev_pos is None:
                    self.bot.prev_pos = self.bot.next_pos
                distance = check_road(self, pos, self.bot.next_pos)
                if distance > 2:
                    self.simulate_input(up=True, sprint=False)
                elif distance >= 0:
                    self.simulate_input(up=True, sprint=False)
                else:
                    print("INVALIDE PATH")
                    self.bot_reset()

            if self.bot.next_pos is not None:
                npos = self.bot.next_pos
                new = (npos-pos)
                new.normalize()
                new.z = min(new.z, 0.5)
                new.normalize()
                if self.check_floor():
                    vel.set(*(new*vel.length()).get())
                self.world_object.set_orientation(*new.get())

                if abs(pos.x-npos.x) < 0.17 and abs(pos.y-npos.y) < 0.17 and abs(pos.z-npos.z) <= 1:
                    # Телепортировать точно в центр, если движение было в одной плоскости
                    # Нужно для точного прохождения узких мест, чтобы не цеплялся за углы
                    #if npos.y == self.bot.prev_pos.y:
                    self.world_object.set_position(npos.x, npos.y, pos.z)
                    self.bot.prev_pos = self.bot.next_pos
                    self.bot.next_pos = None
                    if not self.bot.path:
                        self.simulate_input()
                        vel.zero()

        def bot_think(self):
            self.on_bot_think()
            # unstuck
            if (self.bot.stuck > self.bot.stuck_cup) and self.bot.path:
                if self.world_object.position.z > 61:
                    print(self.player_id, "STUCK IN WATER")
                    self.set_hp(0)
                else:
                    print(self.player_id, "UNSTUCKED")
                    self.bot_reset()
                self.bot.stuck = 0
            self.bot.stuck += 1
            
            if self.bot.target_player is not None:
                if self.bot.target_player.world_object is None:
                    self.bot.target_player = None
                else:
                    pos = self.bot.target_player.world_object.position
                    self.bot.target_pos.x = int(pos.x)
                    self.bot.target_pos.y = int(pos.y)
                    self.bot.target_pos.z = int(pos.z)
            
            if self.world_object.position.distance(self.bot.target_pos) > 1:
                if (not self.bot.task) or (self.bot.task.done()) or (self.bot.task.cancelled()):
                    self.bot.task = asyncio.get_event_loop().create_task(self.bot_pathfind())

        def bot_reset(self, safe_land=True):
            self.simulate_input()
            self.world_object.velocity.zero()
            if safe_land:
                self.set_location_safe(self.world_object.position.get())
            self.bot.path.clear()
            self.bot.next_pos = None
            self.bot.prev_pos = None
            if self.bot.task:
                self.bot.task.cancel()
            pos = self.world_object.position
            self.bot.target_player= None
            self.bot.target_pos = Vertex3(int(pos.x), int(pos.y), int(pos.z))

        def bot_deactivate(self):
            self.bot.active = False
            self.bot_reset(False)

        def on_bot_think(self):
            pass
    
    class BotCoreProtocol(protocol):

        def create_bot(self, team_id=0, weapon_id=0, tool_id=0, name="bot"):
            player = self.connection_class(self, self.host)
            player.disconnected = True
            player.local = True
            player.bot = BotInfo()
            player.player_id = self.player_ids.pop()
            
            packet = loaders.ExistingPlayer()
            packet.player_id = player.player_id
            packet.team = team_id
            packet.weapon = weapon_id
            packet.tool = tool_id
            packet.name = name
            connection.on_new_player_recieved(player, packet)

            player.bot_reset()
            #asyncio.get_event_loop().call_later(0.5, player.bot_loop)
            return player

        def remove_bot(self, player):
            if player.bot.task:
                player.bot.task.cancel()
            player.bot = None
            player.on_disconnect()

        def on_world_update(self):
            for player in self.players.values():
                if player.bot and player.hp and player.bot.active:
                    player.bot_step()
                    if self.loop_count % 60 == player.player_id:
                        player.bot_think()

            return protocol.on_world_update(self)

    return BotCoreProtocol, BotCoreConnection