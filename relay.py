from twisted.internet.protocol import DatagramProtocol
from twisted.internet import reactor
from pyspades.tools import get_server_ip
from pyspades.packet import Packet
from pyspades.common import *
from bytereader import ByteReader

from cStringIO import StringIO

# HOST = '127.0.0.1'
# PORT = 32886

HOST = get_server_ip('aos://1289779525')
PORT = 32887

class ClientProtocol(DatagramProtocol):
    def __init__(self, server):
        self.server = server
    
    def startProtocol(self):
        self.transport.connect(self.server.host, self.server.port)
    
    def datagramReceived(self, data, (host, port)):
        if parse_packet(data, False) == False:
            return
        self.server.transport.write(data, self.server.address)

packet = Packet()

def parse_packet(input, isClient):
    packet.read(input, isClient)
    # if packet.timer is None:
        # offset = 2
    # else:
        # offset = 4
    # fromEnd = ['server', 'client'][int(isClient)]
    
    # printable = '%s %s' % (hexify(input[:offset]), hexify(str(packet.data)))
    # print 'from %s (%s %s):\t%s' % (fromEnd, packet.unique, packet.connectionId, printable)
    # for item in packet.packets:
        # packetId = item.pop(0)
        # elif packetId == 6:
            # item[-1] = hexify(str(item[-1]))
            # print 'from %s -> %s: %s' % (fromEnd, packetId, item)
        # else:
            # pass
            # print '%s: %s' % (packetId, item)

class ServerProtocol(DatagramProtocol):
    def __init__(self, host, port):
        self.host = host
        self.port = port
        self.clientHost = self.clientPort = None
    
    def startProtocol(self):
        self.client = ClientProtocol(self)
        reactor.listenUDP(0, self.client)
        
    def datagramReceived(self, data, (host, port)):
        self.address = (host, port)
        ret = parse_packet(data, True)
        if ret == False:
            return
        self.client.transport.write(data)

reactor.listenUDP(32887, ServerProtocol(HOST, PORT))
reactor.run()