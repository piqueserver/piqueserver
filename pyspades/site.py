from twisted.web.client import getPage
from twisted.internet.defer import Deferred
from collections import namedtuple
from pyspades.tools import get_server_ip

SERVER_LIST = 'http://ace-spades.com/?page_id=5'

START_IDENTIFIER = '<pre>#/MAX PING CNTRY NAME (Click to Join)\n'
END_IDENTIFIER = '</pre>'

ServerEntry = namedtuple('ServerEntry', ['name', 'ip', 'ping', 'players', 
    'max', 'country'])

def got_servers(data, defer):
    start = data.index(START_IDENTIFIER) + len(START_IDENTIFIER)
    end = data.index(END_IDENTIFIER, start)
    data = data[start:end].splitlines()
    servers = []
    for value in data:
        players, max = value[0:5].strip().split('/')
        players = int(players)
        max = int(max)
        ping = int(value[5:10].strip())
        country = value[48:50]
        identifier = value[70:]
        end_start = identifier.index('>')+1
        real_identifier = int(identifier[15:end_start-2])
        ip = get_server_ip(real_identifier)
        name = identifier[end_start:-4]
        servers.append(ServerEntry(name, ip, ping, players, max, country))
    defer.callback(servers)

def get_servers():
    defer = Deferred()
    getPage(SERVER_LIST).addCallback(got_servers, defer)
    return defer