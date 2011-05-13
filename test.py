from pyspades.client import ClientProtocol
from twisted.internet import reactor

class TestProtocol(ClientProtocol):
    pass

HOST = '127.0.0.1'
PORT = 32887

reactor.listenUDP(0, TestProtocol(HOST, 32887))
reactor.run()