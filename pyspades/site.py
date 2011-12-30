from twisted.web.client import getPage
from twisted.internet.defer import Deferred
from collections import namedtuple
from pyspades.tools import get_server_ip
from HTMLParser import HTMLParser

SERVER_LIST = 'http://ace-spades.com/serverlist.txt'

ServerEntry = namedtuple('ServerEntry', ['name', 'ip', 'ping', 'players', 
    'max', 'country'])

class ServerParser(HTMLParser):
    data_index = 0
    
    def reset_server(self):
        self.data_index = 0
    
    def handle_starttag(self, tag, attrs):
        if tag == 'img':
            # country
            url = attrs[0][1]
            self.country = url.split('/')[-1][1:-4]
        elif tag == 'a':
            # identifier (aos://12345678)
            self.ip = get_server_ip(attrs[0][1])
    def handle_data(self, data):
        if self.data_index == 0:
            players, ping = data.rsplit(None, 1)
            count, max = players.split('/')
            self.players = int(count.strip())
            self.max = int(max.strip())
            self.ping = int(ping.strip())
        elif self.data_index == 2:
            self.name = data
        self.data_index += 1

def got_servers(data, defer):
    data = data.splitlines()
    servers = []
    parser = ServerParser()
    for value in data:
        parser.reset_server()
        parser.feed(value)
        servers.append(ServerEntry(parser.name, parser.ip, parser.ping, 
            parser.players, parser.max, parser.country))
    defer.callback(servers)

def get_servers():
    defer = Deferred()
    getPage(SERVER_LIST).addCallback(got_servers, defer)
    return defer