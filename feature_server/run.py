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

frozen = hasattr(sys, 'frozen')

if frozen:
    CLIENT_VERSION = int(open('client_version', 'rb').read())
else:
    sys.path.append('..')
    from pyspades.common import crc32
    CLIENT_VERSION = crc32(open('../data/client.exe', 'rb').read())

if sys.platform == 'win32':
    # install IOCP
    try:
        from twisted.internet import iocpreactor 
        iocpreactor.install()
    except ImportError:
        print '(dependencies missing for fast IOCP, using normal reactor)'

if sys.version_info < (2, 7):
    try:
        import psyco
        psyco.full()
    except ImportError:
        print '(optional: install psyco for optimizations)'

from pyspades.server import ServerProtocol, ServerConnection
from map import Map
from twisted.internet import reactor
from twisted.internet.task import LoopingCall
from pyspades.common import encode, decode
from pyspades.constants import *

import json
import random
import time
import commands

def writelines(fp, lines):
    for line in lines:
        fp.write(line + "\r\n")

class FeatureConnection(ServerConnection):
    admin = False
    last_votekick = None
    mute = False
    login_retries = None
    
    def on_join(self):
        if self.protocol.motd is not None:
            self.send_lines(self.protocol.motd)
    
    def on_login(self, name):
        self.protocol.send_chat('%s entered the game!' % name)
        self.protocol.log('%s (%s) entered the game!' % (name, self.address[0]))
        self.protocol.irc_say( "%s entered the game" % name)
            
    def disconnect(self):
        if self.name is not None:
            self.protocol.send_chat('%s left the game' % self.name)
            self.protocol.log(self.name, 'disconnected!')
            self.protocol.irc_say( "%s disconnected" % self.name)
        ServerConnection.disconnect(self)
    
    def on_command(self, command, parameters):
        log_message = '<%s> /%s %s' % (self.name, command, 
            ' '.join(parameters))
        result = commands.handle_command(self, command, parameters)
        if result is not None:
            log_message += ' -> %s' % result
            self.send_chat(result)
        self.protocol.log(log_message)
    
    def on_block_build(self, x, y, z):
        if not self.protocol.building:
            return False
        
    def on_block_destroy(self, x, y, z, mode):
        if self.protocol.indestructable_blocks:
            is_indestructable = self.protocol.is_indestructable
            if mode == DESTROY_BLOCK:
                if is_indestructable(x, y, z):
                    return False
            elif mode == SPADE_DESTROY:
                if (is_indestructable(x, y, z) or
                is_indestructable(x, y, z + 1) or
                is_indestructable(x, y, z - 1)):
                    return False
            elif mode == GRENADE_DESTROY:
                for nade_x in xrange(x - 1, x + 2):
                    for nade_y in xrange(y - 1, y + 2):
                        for nade_z in xrange(z - 1, z + 2):
                            if is_indestructable(nade_x, nade_y, nade_z):
                                return False

        if not self.protocol.building:
            return False
    
    def on_hit(self, hit_amount, player):
        if not self.protocol.killing:
            return False
    
    def on_grenade(self, time_left):
        if not self.protocol.killing:
            return False
    
    def on_team_join(self, team):
        if team.locked:
            self.send_chat('Team is locked.')
            return False
        balanced_teams = self.protocol.balanced_teams
        if not balanced_teams:
            return
        other_team = team.other
        if other_team.count() < team.count() + 1 - balanced_teams:
            self.send_chat('Team is full. Please join the other team')
            return False
    
    def on_chat(self, value, global_message):
        message = '<%s> %s' % (self.name, value)
        if self.mute:
            message = '(MUTED) %s' % message
        elif global_message:
            self.protocol.irc_say("<%s> %s" % (self.name, value))
        self.protocol.log(message)
        if self.mute:
            self.send_chat('(Chat not sent - you are muted)')
            return False
    
    def kick(self, reason = None, silent = False):
        if not silent:
            if reason is not None:
                message = '%s was kicked: %s' % (self.name, reason)
            else:
                message = '%s was kicked' % self.name
            self.protocol.send_chat(message)
            self.protocol.irc_say(message)
        self.disconnect()
    
    def ban(self, reason = None):
        if reason is not None:
            message = '%s banned: %s' % (self.name, reason)
        else:
            message = '%s banned' % self.name
        self.protocol.send_chat(message)
        self.protocol.irc_say(message)
        self.protocol.add_ban(self.address[0])
    
    def send_lines(self, lines):
        current_time = 0
        for line in lines:
            reactor.callLater(current_time, self.send_chat, line)
            current_time += 2

def encode_lines(value):
    if value is not None:
        lines = []
        for line in value:
            lines.append(encode(line))
        return lines

def make_range_object(value):
    if len(value) == 1:
        return xrange(value, value + 1)
    return xrange(value[0], value[1])
        
class FeatureProtocol(ServerProtocol):
    connection_class = FeatureConnection
    version = CLIENT_VERSION
    admin_passwords = None
    bans = None
    timestamps = None
    logfile = None
    irc_relay = None
    balanced_teams = None
    building = True
    killing = True
    remote_console = None
    # votekick
    votekick_time = 60 # 1 minute
    votekick_interval = 3 * 60 # 3 minutes
    votekick_percentage = 25.0
    votekick_max_percentage = 40.0 # too many no-votes?
    votes_left = None
    votekick_player = None
    voting_player = None
    votes = None
    
    map_info = None
    indestructable_blocks = None
    
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
            map = Map(config['map'])
            self.map = map.data
            self.map_info = map
        except KeyError:
            print 'no map specified!'
            return
        except IOError:
            print 'map not found!'
            return
        self.indestructable_blocks = indestructable_blocks = []
        for r, g, b in map.indestructable_blocks:
            r = make_range_object(r)
            g = make_range_object(g)
            b = make_range_object(b)
            indestructable_blocks.append((r, g, b))
            
        self.max_scores = config.get('cap_limit', None)
        self.respawn_time = config.get('respawn_time', 5)
        self.master = config.get('master', True)
        self.friendly_fire = config.get('friendly_fire', True)
        self.motd = self.format_lines(config.get('motd', None))
        self.max_players = config.get('max_players', 20)
        passwords = config.get('passwords', {})
        self.admin_passwords = passwords.get('admin', [])
        self.server_prefix = encode(config.get('server_prefix', '[*]'))
        self.timestamps = config.get('timestamps', False)
        self.balanced_teams = config.get('balanced_teams', None)
        self.rules = self.format_lines(config.get('rules', None))
        self.login_retries = config.get('login_retries', 1)
        logfile = config.get('logfile', None)
        ssh = config.get('ssh', {})
        if ssh.get('enabled', False):
            from ssh import RemoteConsole
            self.remote_console = RemoteConsole(self, ssh)
        irc = config.get('irc', {})
        if irc.get('enabled', False):
            from irc import IRCRelay
            self.irc_relay = IRCRelay(self, irc)
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
        # locked teams
        self.blue_team.locked = False
        self.green_team.locked = False
    
    def is_indestructable(self, x, y, z):
        r, g, b = self.map.get_point(x, y, z)[1][:-1]
        for r_range, g_range, b_range in self.indestructable_blocks:
            if r in r_range and g in g_range and b in b_range:
                return True
        return False
    
    def format_lines(self, value):
        if value is None:
            return
        map = self.map_info
        format_dict = {
            'server_name' : self.name,
            'map_name' : map.name,
            'map_author' : map.author,
            'map_description' : map.description
        }
        lines = []
        for line in value:
            lines.append(encode(line % format_dict))
        return lines
        
    def got_master_connection(self, *arg, **kw):
        print 'Master connection established.'
        ServerProtocol.got_master_connection(self, *arg, **kw)
    
    def master_disconnected(self, *arg, **kw):
        print 'Master connection lost, reconnecting...'
        ServerProtocol.master_disconnected(self, *arg, **kw)
        
    def add_ban(self, ip):
        for connection in self.connections.values():
            if connection.address[0] == ip:
                connection.kick(silent = True)
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
        
    def irc_say(self, msg):
        if self.irc_relay:
            self.irc_relay.send(msg)
    
    # votekick
    
    def start_votekick(self, connection, player):
        if self.votes is not None:
            return 'Votekick in progress.'
        last_votekick = connection.last_votekick
        if (last_votekick is not None and 
        reactor.seconds() - last_votekick < self.votekick_interval):
            return "You can't start a votekick now."
        votes_left = int((len(self.players) / 100.0
            ) * self.votekick_percentage)
        if votes_left == 0:
            return 'Not enough players on server.'
        self.votes_left = votes_left
        self.votes = {connection : True}
        votekick_time = self.votekick_time
        self.votekick_call = reactor.callLater(votekick_time, 
            self.end_votekick, False, 'Votekick timed out')
        self.send_chat('%s initiated a VOTEKICK against player %s. '
            'Say /y to agree and /n to decline.' % (connection.name, 
            player.name), sender = connection)
        self.irc_say(
            '%s initiated a votekick against player %s.' % (connection.name, 
            player.name))
        self.votekick_player = player
        self.voting_player = connection
        return 'You initiated a votekick. Say /cancel to stop it at any time.'
    
    def votekick(self, connection, value):
        if self.votes is None or connection in self.votes:
            return
        if value:
            self.votes_left -= 1
        else:
            self.votes_left += 1
        max = int((len(self.players) / 100.0) * self.votekick_max_percentage)
        if self.votes_left >= max:
            self.votekick_call.cancel()
            self.end_votekick(False, 'Too many negative votes')
            return
        self.votes[connection] = value
        if self.votes_left:
            self.send_chat('%s voted %s. %s more players required.' % (
                connection.name, ['NO', 'YES'][int(value)], self.votes_left))
        else:
            self.votekick_call.cancel()
            self.end_votekick(True, 'Player kicked')
    
    def cancel_votekick(self, connection):
        if self.votes is None:
            return 'No votekick in progress.'
        if not connection.admin and connection is not self.voting_player:
            return 'You did not start the votekick.'
        self.votekick_call.cancel()
        self.end_votekick(False, 'Cancelled by %s' % connection.name)
    
    def end_votekick(self, enough, result):
        message = 'Votekick for %s has ended. %s.' % (
            self.votekick_player.name, result)
        self.send_chat(message, irc = True)
        connection.protocol.irc_relay.send(message)
        if enough:
            self.votekick_player.kick(silent = True)
        elif not self.voting_player.admin: # admins are powerful, yeah
            self.voting_player.last_votekick = reactor.seconds()
        self.votes = self.votekick_call = self.votekick_player = None
        self.voting_player = None
    
    def send_chat(self, value, global_message = True, sender = None, irc = False):
        if irc:
            self.irc_say(value)
        ServerProtocol.send_chat(self, value, global_message, sender)

PORT = 32887

reactor.listenUDP(PORT, FeatureProtocol())
print 'Started server on port %s...' % PORT
reactor.run()