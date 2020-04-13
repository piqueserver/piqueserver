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

def check_road(player, p1, p2):
    solid = player.protocol.map.get_solid
    def solid3(x, y ,z):
        return not(solid(x, y, z) or solid(x, y, z + 1) or solid(x, y, z + 2))
    x1, y1, z1 = p1.get()
    x2, y2, z2 = p2.get()
    z = min(z1, z2)
    if not solid3(x1, y1, z1) or not solid3(x2, y2, z2):
        return -1
    if x1 != x2 and y1 != y2:
        if not solid3(x1, y2, z) or not solid3(x2, y1, z):
            return -1
    return p1.distance(p2)


class BotInfo:
    target_player = None
    target_pos = Vertex3(0, 0, 0)
    attacking = False
    next_pos = None
    prev_pos = None
    stuck = 0
    task = None
    path = []

def apply_script(protocol, connection, config):

    class BotCoreConnection(connection):
        bot = None

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

        def check_floor(self):
            if abs(self.world_object.velocity.z) > 0.0005:
                return False
            pos = self.world_object.position
            return self.protocol.map.get_solid(pos.x, pos.y, pos.z + 3)

        async def bot_pathfind(self):
            #while not self.check_floor():
            #    await asyncio.sleep(1/60)
            pos = self.world_object.position.copy()
            pos.x = int(pos.x)
            pos.y = int(pos.y)
            pos.z = int(pos.z)
            target = self.bot.target_pos
            path = self.bot.path

            if path:
                best_i = -1
                best_dist = 9999999
                if self.bot.next_pos is None:
                    prev_pos = pos
                else:
                    prev_pos = self.bot.next_pos
                for i in range(0, len(path)):
                    p = Vertex3(path[i][0], path[i][1], path[i][2])
                    if check_road(self, prev_pos, p) == -1:
                        #print(prev_pos)
                        #print(p)
                        break
                    dist = p.distance(target)
                    if dist <= best_dist:
                        best_dist = dist
                        best_i = i
                    prev_pos = p
                #print(str(best_i+1)+" / "+str(len(path)))
                if best_i >= 0:
                    pos = Vertex3(path[best_i][0], path[best_i][1], path[best_i][2])
                self.bot.path = path[0:best_i+1]
            await asyncio.sleep(0)
            if pos.distance(target) > 1:
                #print(pos.distance(target))
                self.bot.path.extend(self.protocol.map.a_star(int(pos.x), int(pos.y), int(pos.z),
                    int(target.x), int(target.y), int(target.z), False, False))

        def bot_step(self):
            pos = self.world_object.position
            vel = self.world_object.velocity
            if (self.bot.next_pos is None) and self.bot.path and self.check_floor():
                self.bot.stuck = 0
                self.bot.next_pos = Vertex3(*self.bot.path.pop(0))
                self.bot.next_pos.x += 0.5
                self.bot.next_pos.y += 0.5
                self.bot.next_pos.z += 0.748 # Head offset
                #print('==========')
                if self.bot.prev_pos is None:
                    self.bot.prev_pos = self.bot.next_pos
                distance = check_road(self, self.bot.prev_pos, self.bot.next_pos)
                if distance > 1.8:
                    self.simulate_input(up=True, sprint=True)
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
            if self.tool != SPADE_TOOL:
                self.simulate_tool_change(SPADE_TOOL)
            # unstuck
            if self.bot.stuck > 12 and self.bot.path: #2.2 sec
                self.bot_reset()
                self.bot.stuck = 0
                print("UNSTUCKED")
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

        def bot_reset(self):
            self.simulate_input()
            self.world_object.velocity.zero()
            self.set_location_safe(self.world_object.position.get())
            self.bot.path.clear()
            self.bot.next_pos = None
            self.bot.prev_pos = None
            if self.bot.task:
                self.bot.task.cancel()
            pos = self.world_object.position
            self.bot.target_pos = Vertex3(int(pos.x), int(pos.y), int(pos.z))

    
    class BotCoreProtocol(protocol):

        def create_bot(self, team_id=0, weapon_id=0, name="bot"):
            player = BotCoreConnection(self, self.host)
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
                if player.bot:
                    player.bot_step()
                    if self.loop_count % 11 == 0:
                        player.bot_think()

            return protocol.on_world_update(self)

    return BotCoreProtocol, BotCoreConnection