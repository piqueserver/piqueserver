from twisted.internet.protocol import DatagramProtocol
from twisted.internet import reactor
from pyspades.tools import get_server_ip
from pyspades.packet import Packet
from pyspades.common import *
from pyspades.loaders import *
from pyspades import debug
debug.is_relay = True

from cStringIO import StringIO

HOST = '127.0.0.1'
PORT = 32886

# HOST = get_server_ip('aos://1656594257')
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
    printable = '%s %s' % (hexify(input[:offset]), hexify(str(packet.data)))
    print 'from %s (%s %s):\t%s' % (get_name(isClient), packet.unique, packet.connectionId, printable)

def print_packet_list(packet, isClient):
    print 'from %s:\t%s' % (get_name(isClient), packet.packets)

def get_name(isClient):
    return ['server', 'client'][int(isClient)]

server_seq = 0
client_seq = 0

server_seqs = set()
client_seqs = set()

def is_clean(the_set):
    start = 1
    gap = []
    for value in sorted(the_set):
        if value != start:
            while start < value:
                gap.append(start)
                start += 1
        start += 1
    return gap

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
    # global server_seq
    # global client_seq
    # for item in packet.packets[:]:
        # sequence = item.sequence
        # if item.id == Ack.id:
            
        # print get_name(isClient), item.sequence, item
        # if item.byte != 0:
            # print 'WTF!?', get_name(isClient), item.byte, item
        # else:
            # if isClient:
                # if sequence < client_seq:
                    # print 'what? client', client_seq
                # else:
                    # client_seq = sequence
                # client_seqs.add(sequence)
            # else:
                # if sequence < server_seq:
                    # print 'what? server', client_seq
                # else:
                    # server_seq = sequence
                # server_seqs.add(sequence)
    
    # print 'client clean:', is_clean(client_seqs)
    # print 'server clean:', is_clean(server_seqs)
        # item.byte = 0
    # print_packet(input, packet, isClient)
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