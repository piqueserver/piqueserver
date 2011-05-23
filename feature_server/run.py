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

class FeatureConnection(ServerConnection):
    def disconnect(self):
        print self.name, 'disconnected!'
        ServerConnection.disconnect(self)

class FeatureProtocol(ServerProtocol):
    version = crc32(open('../data/client.exe', 'rb').read())
    
    def __init__(self):
        self.config = config = json.load(open('config.txt', 'rb'))
        self.name = config['name']
        self.map = VXLData(open(config['map'], 'rb'))
        self.max_scores = config['cap_limit']
        self.respawn_time = config['respawn_time']
        self.master = config['master']
        self.friendly_fire = config['friendly_fire']
        ServerProtocol.__init__(self)

PORT = 32887

reactor.listenUDP(PORT, FeatureProtocol())
print 'Started server on port %s...' % PORT
reactor.run()