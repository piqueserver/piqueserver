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
import time
import commands

def writelines(fp, lines):
    for line in lines:
        fp.write(line + "\r\n")

class FeatureConnection(ServerConnection):
    admin = False
    votekick_loop = None
    votekick_call = None
    votekicks = None
    
    def on_join(self):
        if self.protocol.motd is not None:
            self.send_chat(self.protocol.motd)
    
    def on_login(self, name):
        self.protocol.log('%s (%s) entered the game!' % (name, self.address[0]))
    
    def disconnect(self):
        if self.name is not None:
            self.protocol.log(self.name, 'disconnected!')
        ServerConnection.disconnect(self)
    
    def on_command(self, command, parameters):
        log_message = '<%s> /%s %s' % (self.name, command, 
            ' '.join(parameters))
        result = commands.handle_command(self, command, parameters)
        if result is not None:
            log_message += ' -> %s' % result
            self.send_chat(result)
        self.protocol.log(log_message)
    
    def accept_chat(self, value, global_message):
        pass
    
    def accept_team_join(self, team):
        balanced_teams = self.protocol.balanced_teams
        if not balanced_teams:
            return
        other_team = team.other
        if len(other_team) < len(team) + 1 - balanced_teams:
            self.send_chat('Team is full. Please join the other team')
            return False
    
    def on_chat(self, value, global_message):
        self.protocol.log('<%s> %s' % (self.name, value))
    
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
    
    def ban(self, reason = None):
        if reason is not None:
            message = '%s banned: %s' % (self.name, reason)
        else:
            message = '%s banned' % self.name
        self.protocol.send_chat(message)
        self.protocol.add_ban(self.address[0])

class FeatureProtocol(ServerProtocol):
    connection_class = FeatureConnection
    version = crc32(open('../data/client.exe', 'rb').read())
    admin_passwords = None
    votekick_time = 60 # 1 minute
    votekick_percentage = 25.0
    bans = None
    timestamps = None
    logfile = None
    balanced_teams = None
    
    def __init__(self):
        try:
            config = json.load(open('config.txt', 'rb'))
        except IOError:
            print 'no config.txt file found'
            return
        try:
            self.bans = set(json.load(open('bans.txt', 'rb')))
        except IOError:
            self.bans = set([])
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
        self.server_prefix = config.get('server_prefix', '[*]')
        self.timestamps = config.get('timestamps', False)
        self.balanced_teams = config.get('balanced_teams', None)
        logfile = config.get('logfile', None)
        if logfile is not None and logfile.strip():
            self.logfile = open(logfile, 'ab')
            writelines(self.logfile, [
                '',
                'pyspades server started on %s' % time.strftime('%c')
            ])
            
        for password in self.admin_passwords:
            if password == 'replaceme':
                self.log(
                    'REMEMBER TO CHANGE THE DEFAULT ADMINISTRATOR PASSWORD!')
                break
        ServerProtocol.__init__(self)
    
    def add_ban(self, ip):
        for address, connection in self.connections.iteritems():
            if address[0] == ip:
                connection.kick()
        self.bans.add(ip)
        json.dump(list(self.bans), open('bans.txt', 'wb'))
    
    def datagramReceived(self, data, address):
        if address[0] in self.bans:
            return
        ServerProtocol.datagramReceived(self, data, address)
    
    def log(self, *arg):
        value = ' '.join(arg)
        if self.timestamps:
            value = '%s %s' % (time.strftime('[%X]'), value)
        if self.logfile:
            writelines(self.logfile, [value])
        print value

PORT = 32887

reactor.listenUDP(PORT, FeatureProtocol())
print 'Started server on port %s...' % PORT
reactor.run()