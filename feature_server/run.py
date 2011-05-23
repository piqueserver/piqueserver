"""
pyspades - default/featured server
"""

import sys
sys.path.append('..')

from pyspades.server import ServerProtocol
from pyspades.load import VXLData
from twisted.internet import reactor
from pyspades.common import crc32

class TestProtocol(ServerProtocol):
    map = VXLData(open('../data/sinc0.vxl', 'rb'))
    version = crc32(open('../data/client.exe', 'rb').read())

PORT = 32887

reactor.listenUDP(PORT, TestProtocol())
print 'Started server on port %s...' % PORT
reactor.run()