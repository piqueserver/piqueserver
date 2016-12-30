# Copyright (c) Mathias Kaerlev 2011-2012.

# This file is part of pyspades.

# pyspades is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

# pyspades is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with pyspades.  If not, see <http://www.gnu.org/licenses/>.

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
