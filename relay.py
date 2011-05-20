from twisted.internet.protocol import DatagramProtocol
from twisted.internet import reactor
from pyspades.tools import get_server_ip
from pyspades.packet import Packet, load_server_packet, load_client_packet
from pyspades import clientloaders, serverloaders
from pyspades.common import *
from pyspades.loaders import *
from pyspades import debug
from pyspades.bytereader import ByteReader
debug.is_relay = True

from cStringIO import StringIO

HOST = '127.0.0.1'
# PORT = 32885
PORT = 32886

# HOST = get_server_ip('aos://1289779525')
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
    print 'from %s (%s %s):\t%s' % (get_name(isClient), packet.unique, packet.connection_id, printable)

def print_packet_list(packet, isClient):
    print 'from %s:\t%s' % (get_name(isClient), packet.items)

def get_name(isClient):
    return ['server', 'client'][int(isClient)]

def print_item(item):
    print item,
    try:
        printable = hexify(str(item.data)),
        firstByte = ord(str(item.data)[0])
        type = firstByte & 0xF
        print type, printable
    except AttributeError:
        pass
    print ''
    
def parse_packet(input, isClient):
    packet.read(input)
    # print 'received packet:', vars(packet)
    # print get_name(isClient), packet.items
    for item in packet.items[:]:
        # print get_name(isClient), item, item.sequence, item.byte, item.ack
        if hasattr(item, 'data') and item.id != MapData.id:
            orig = str(item.data)
            if isClient:
                contained = load_client_packet(item.data)
            else:
                contained = load_server_packet(item.data)
            # print contained
            if item.data.dataLeft():
                raw_input('packet not properly parsed')
            reader = ByteReader()
            contained.write(reader)
            if contained.id == 12:
                print '12!', vars(contained)
            else:
                if orig != str(reader):
                    print contained.id, 'not written correctly', isClient
                    print hexify(orig)
                    print hexify(str(reader))
            item.data = reader
        elif item.id in (Ack.id,):
            continue

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