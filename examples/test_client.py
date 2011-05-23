from pyspades.client import ClientProtocol
from twisted.internet import reactor
from pyspades.tools import *

class TestProtocol(ClientProtocol):
    pass

HOST = get_server_ip('aos://458956633')
PORT = 32887

reactor.listenUDP(0, TestProtocol(HOST, PORT))
reactor.run()