from pyspades.client import ClientProtocol
from twisted.internet import reactor
from pyspades.tools import *

class TestProtocol(ClientProtocol):
    pass

HOST = '127.0.0.1'
PORT = 32886

# HOST = get_server_ip('aos://626598556')
# PORT = 32887

reactor.listenUDP(0, TestProtocol(HOST, PORT))
reactor.run()