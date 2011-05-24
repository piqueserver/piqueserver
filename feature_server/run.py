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
from pyspades.common import crc32

import json
import random
import commands

class FeatureConnection(ServerConnection):
    def disconnect(self):
        print self.name, 'disconnected!'
        ServerConnection.disconnect(self)
    
    def on_command(self, command, parameters):
        self.protocol.send_chat("HI FROM THE SERVER :-)")
        # commands.handle_command(self, command, parameters)
    
    def accept_chat(self, value, global_message):
        pass
    
    def on_chat(self, value, global_message):
        print '<%s> %s' % (self.name, value)

class FeatureProtocol(ServerProtocol):
    connection_class = FeatureConnection
    version = crc32(open('../data/client.exe', 'rb').read())
    admin_passwords = None
    
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