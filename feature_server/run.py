# Copyright (c) Mathias Kaerlev 2011.

# This file is part of pyspades.

# pyspades is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

# pyspades is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with pyspades.  If not, see <http://www.gnu.org/licenses/>.

"""
pyspades - default/featured server
"""

import sys
sys.path.append('..')

from pyspades.server import ServerProtocol, ServerConnection
from pyspades.load import VXLData
from twisted.internet import reactor
from twisted.internet.task import LoopingCall
from pyspades.common import crc32

import json
import random
import commands

class FeatureConnection(ServerConnection):
    admin = False
    votekick_loop = None
    votekick_call = None
    votekicks = None
    
    def on_join(self):
        if self.protocol.motd is not None:
            self.send_chat(self.protocol.motd)
        
    def disconnect(self):
        print self.name, 'disconnected!'
        ServerConnection.disconnect(self)
    
    def on_command(self, command, parameters):
        result = commands.handle_command(self, command, parameters)
        if result is not None:
            self.send_chat(result)
    
    def accept_chat(self, value, global_message):
        pass
    
    def on_chat(self, value, global_message):
        print '<%s> %s' % (self.name, value)
    
    def votekick(self, by, reason = None):
        if self.votekicks is None:
            self.protocol.send_chat('Votekick initiated for %s: %s' % (
                self.name, reason or 'No reason specified'))
            self.votekicks = set([by])
            votekick_time = self.protocol.votekick_time
            self.votekick_call = reactor.callLater(votekick_time, 
                self.end_votekick, 'Not enough votes')
            self.votekick_loop = LoopingCall(self.update_votekick)
            self.votekick_loop.start(votekick_time / 10.0, False)
        else:
            self.votekicks.add(by)
        value = int((len(self.votekicks) / float(len(self.protocol.players))
            ) * 100.0)
        if value >= self.protocol.votekick_percentage:
            self.disconnect()
            self.end_votekick('Player kicked')
    
    def update_votekick(self):
        if not self.protocol.players: # no ZeroDivisionErrors for me!
            return
        value = int((len(self.votekicks) / float(len(self.protocol.players))
            ) * 100.0)
        self.protocol.send_chat('Votekick for %s at %s' % (self.name,
            value))
    
    def end_votekick(self, result):
        self.protocol.send_chat('Votekick ended for %s: %s' % (
            self.name, result))
        self.votekick_loop.stop()
        self.votekick_call.cancel()
        self.votekick_loop = self.votekicks = self.votekick_call = None
    
    def kick(self, reason = None):
        if reason is not None:
            message = '%s kicked: %s' % (self.name, reason)
        else:
            message = '%s kicked' % self.name
        self.protocol.send_chat(message)
        self.disconnect()

class FeatureProtocol(ServerProtocol):
    connection_class = FeatureConnection
    version = crc32(open('../data/client.exe', 'rb').read())
    admin_passwords = None
    votekick_time = 60 # 1 minute
    votekick_percentage = 25.0
    
    def __init__(self):
        try:
            config = json.load(open('config.txt', 'rb'))
        except IOError:
            print 'no config.txt file found'
            return
        self.config = config
        self.name = config.get('name', 
            'pyspades server %s' % random.randrange(0, 2000))
        try:
            self.map = VXLData(open(config['map'], 'rb'))
        except KeyError:
            print 'no map specified!'
            return
        except IOError:
            print 'map not found!'
            return
        self.max_scores = config.get('cap_limit', None)
        self.respawn_time = config.get('respawn_time', 5)
        self.master = config.get('master', True)
        self.friendly_fire = config.get('friendly_fire', True)
        self.motd = config.get('motd', None)
        self.max_players = config.get('max_players', 20)
        passwords = config.get('passwords', {})
        self.admin_passwords = passwords.get('admin', [])
        for password in self.admin_passwords:
            if password == 'replaceme':
                print 'REMEMBER TO CHANGE THE DEFAULT ADMINISTRATOR PASSWORD!'
                break
        ServerProtocol.__init__(self)

PORT = 32887

reactor.listenUDP(PORT, FeatureProtocol())
print 'Started server on port %s...' % PORT
reactor.run()