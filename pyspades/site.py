from twisted.web.client import getPage
from twisted.internet.defer import Deferred
from collections import namedtuple
from pyspades.tools import get_server_ip

SERVER_LIST = 'http://ace-spades.com/?page_id=5'

START_IDENTIFIER = '<pre>#/MAX PING NAME (Click to Join)\n'
END_IDENTIFIER = '</pre>'

ServerEntry = namedtuple('ServerEntry', ['name', 'ip', 'ping', 'players', 
    'max'])

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
        identifier = value[11:]
        end_start = identifier.index('>')+1
        ip = get_server_ip(int(identifier[15:end_start-2]))
        name = identifier[end_start:-4]
        servers.append(ServerEntry(name, ip, ping, players, max))
    defer.callback(servers)

def get_servers():
    defer = Deferred()
    getPage(SERVER_LIST).addCallback(got_servers, defer)
    return defer