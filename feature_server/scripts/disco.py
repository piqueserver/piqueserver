"""
Ever wanted a disco in Ace of Spades?

Maintainer: mat^2
"""

from twisted.internet.task import LoopingCall
from twisted.internet.reactor import callLater
import random

import commands

DISCO_ON_GAME_END = True
# Time is in seconds
DISCO_ON_GAME_END_DURATION = 10.0

@commands.name('disco')
@commands.admin
def toggle_disco(connection):
    connection.protocol.toggle_disco(True)

commands.add(toggle_disco)

DISCO_COLORS = set([
    (235, 64, 0),
    (128, 232, 121),
    (220, 223, 12),
    (43, 72, 228),
    (216, 94, 231),
    (255, 255, 255)
])

def apply_script(protocol, connection, config):
    class DiscoProtocol(protocol):
        current_colors = None
        disco = False
        old_fog_color = None
        def __init__(self, *arg, **kw):
            protocol.__init__(self, *arg, **kw)
            self.disco_loop = LoopingCall(self.update_color)

        def update_color(self):
            if not self.current_colors:
                self.current_colors = DISCO_COLORS.copy()
            color = self.current_colors.pop()
            self.set_fog_color(color)

        def on_game_end(self):
            if not self.disco and DISCO_ON_GAME_END:
                self.toggle_disco(False)
                callLater(DISCO_ON_GAME_END_DURATION, self.stop_disco)
            return protocol.on_game_end(self)

        def stop_disco(self):
            if self.disco:
                self.toggle_disco(False)

        def toggle_disco(self, message = False):
            self.disco = not self.disco
            if self.disco:
                self.old_fog_color = self.fog_color
                self.disco_loop.start(0.3)
                if message:
                    self.send_chat('DISCO PARTY MODE ENABLED!')
            else:
                self.disco_loop.stop()
                if self.old_fog_color is not None:
                    self.set_fog_color(self.old_fog_color)
                if message:
                    self.send_chat('The party has been stopped.')
    return DiscoProtocol, connection
