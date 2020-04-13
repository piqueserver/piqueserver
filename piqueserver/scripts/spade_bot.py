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


@command('t', admin_only=False)
def test(connection):
    for player in list(connection.protocol.players.values()):
        if player.bot:
            player.bot.target_player = connection
            '''
            pos = player.world_object.position
            target = connection.protocol.players[0].world_object.position
            lag = time.monotonic()
            res = player.protocol.map.a_star(pos.x, pos.y, pos.z, target.x, target.y, target.z, True, False)
            print(time.monotonic() - lag)
            for p in res:
                player.protocol.build_block(p[0], p[1], p[2]+3)
            '''

def apply_script(protocol, connection, config):

    class SpadeBotConnection(connection):
        pass
   
    class SpadeBotProtocol(protocol):
        def on_game_start(self):
            while len(self.players) < 6:
                player = self.create_bot()
                #player.set_location(connection.protocol.players[0].world_object.position.get())
            protocol.on_game_start(self)

        def on_game_end(self):
            for player in list(self.players.values()):
                if player.bot:
                    self.remove_bot(player)
            protocol.on_game_end(self)

    return SpadeBotProtocol, SpadeBotConnection