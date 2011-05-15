from twisted.internet.protocol import DatagramProtocol
from twisted.internet import reactor
from pyspades.tools import get_server_ip
from pyspades.packet import Packet
from pyspades.common import *
from bytereader import ByteReader
from pyspades.loaders import *

from cStringIO import StringIO

HOST = '127.0.0.1'
PORT = 32886

# HOST = get_server_ip('aos://922725974')
# PORT = 32887

class ClientProtocol(DatagramProtocol):
    def __init__(self, server):
        self.server = server
    
    def startProtocol(self):
        self.transport.connect(self.server.host, self.server.port)
    
    def datagramReceived(self, data, (host, port)):
        if parse_packet(data, False) == False:
            return
        self.server.transport.write(str(packet.generate()), self.server.address)
        # self.server.transport.write(data, self.server.address)

packet = Packet()

def print_packet(input, packet, isClient):
    if packet.timer is None:
        offset = 2
    else:
        offset = 4
    fromEnd = ['server', 'client'][int(isClient)]
    
    printable = '%s %s' % (hexify(input[:offset]), hexify(str(packet.data)))
    print 'from %s (%s %s):\t%s' % (fromEnd, packet.unique, packet.connectionId, printable)

def print_packet_list(packet, isClient):
    fromEnd = ['server', 'client'][int(isClient)]
    print 'from %s:\t%s' % (fromEnd, packet.packets)

def parse_packet(input, isClient):
    packet.read(input, isClient)
    # for item in packet.packets[:]:
        # if item.id in (Packet10.id, Packet8.id):
            # if item.id == Packet8.id:
                # print '(got map data)'
            # packet.packets.remove(item)
    # if not packet.packets:
        # return False
    
    # print_packet_list(packet, isClient)
    # for item in packet.packets:
        # print item.id
        # if item.id in (10, 1):
            # return False
    
    # print_packet(packet, isClient)
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
        if parse_packet(data, True) == False:
            return
        self.client.transport.write(str(packet.generate()))
        # self.client.transport.write(data)

reactor.listenUDP(32887, ServerProtocol(HOST, PORT))
reactor.run()