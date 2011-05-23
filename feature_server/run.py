"""
pyspades - default/featured server
"""

from pyspades.server import ServerProtocol
from pyspades.load import VXLData
from twisted.internet import reactor

class TestProtocol(ServerProtocol):
    map = VXLData(open('../examples/sinc0.vxl', 'rb'))

PORT = 32887

reactor.listenUDP(PORT, TestProtocol())
print 'Started server on port %s...' % PORT
reactor.run()