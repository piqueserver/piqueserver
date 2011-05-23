"""
pyspades - default/featured server
"""

import sys
sys.path.append('..')

from pyspades.server import ServerProtocol
from pyspades.load import VXLData
from twisted.internet import reactor
from pyspades.common import crc32

import json

class TestProtocol(ServerProtocol):
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

reactor.listenUDP(PORT, TestProtocol())
print 'Started server on port %s...' % PORT
reactor.run()