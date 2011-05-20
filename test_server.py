from pyspades.server import ServerProtocol
from twisted.internet import reactor

class TestProtocol(ServerProtocol):
    pass

PORT = 32887

reactor.listenUDP(PORT, TestProtocol())
print 'Started server on port %s...' % PORT
reactor.run()