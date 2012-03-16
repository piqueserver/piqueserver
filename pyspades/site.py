from twisted.web.client import getPage
from twisted.internet.defer import Deferred
from collections import namedtuple
from pyspades.tools import get_server_details
import json

SERVER_LIST = 'http://ace-spades.com/serverlist.json'

class ServerEntry(object):
    def __init__(self, value):
        for k, v in value.iteritems():
            setattr(self, k, v)

def got_servers(data, defer):
    data = json.loads(data)
    entries = []
    for entry in data:
        ip, port = get_server_details(entry['identifier'])
        entry['ip'] = ip
        entry['port'] = port
        entries.append(ServerEntry(entry))
    defer.callback(entries)

def get_servers():
    defer = Deferred()
    getPage(SERVER_LIST).addCallback(got_servers, defer)
    return defer