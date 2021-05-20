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

@command('t', admin_only=False)
def test(connection):
    for player in list(connection.protocol.players.values()):
        if player.bot:
            '''
            if player.bot.active:
                player.bot_deactivate()
            else:
                #player.bot.target_player = connection
                player.bot.active = True
            '''
            player.bot_think()
            player.bot.active = False
            connection.protocol.create_bot()

def apply_script(protocol, connection, config):

    class SpadeBotConnection(connection):
        def follow_closest_enemy(self):
            if self.bot.target_player:
                best_dist = self.world_object.position.distance(self.bot.target_player.world_object.position)
            else:
                best_dist = 99999
            self.bot.target_player = None
            for enemy in self.team.other.get_players():
                if not enemy.hp:
                    continue
                dist = self.world_object.position.distance(enemy.world_object.position)
                if best_dist >= dist:
                    best_dist = dist
                    self.bot.target_player = enemy
                    self.bot.active = True

        def on_bot_think(self):
            self.simulate_tool_change(SPADE_TOOL) # TODO FIX weapon instead spade
            self.follow_closest_enemy()
   
    class SpadeBotProtocol(protocol):
        def on_game_start(self):
            while len(self.players) < 10:
                player = self.create_bot()
            protocol.on_game_start(self)

        def on_game_end(self):
            for player in list(self.players.values()):
                if player.bot:
                    self.remove_bot(player)
            protocol.on_game_end(self)

        def on_world_update(self):
            if self.loop_count % 10 == 0:
                for player in self.players.values():
                    if not(player.bot and player.hp):
                        continue
                    if player.bot.target_player and player.bot.target_player.hp:
                        pos = player.world_object.position
                        tpos = player.bot.target_player.world_object.position
                        if check_straight_road(player, pos, tpos) >= 0:
                            player.bot.active = False
                            player.simulate_input(up=True, sprint=False)
                            player.simulate_weapon_input()
                            player.world_object.set_orientation(*(tpos - pos).get())
                            if pos.distance(tpos) < 3:
                                player.bot.target_player.hit(20, player, MELEE_KILL)
                        else:
                            player.bot.active = True
                            player.simulate_weapon_input(False)
                    else:
                        player.simulate_weapon_input(False)
                        player.bot_deactivate()
                        player.follow_closest_enemy()

            return protocol.on_world_update(self)

    return SpadeBotProtocol, SpadeBotConnection