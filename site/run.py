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

import sys
import os

args = sys.argv[1:]

if len(args) not in (1, 2):
    raise SystemExit('usage: %s <port> [stats pass]' % sys.argv[0])

port = int(args[0])
if len(args) == 2:
    stats_pass = args[1]
else:
    stats_pass = None

sys.path.append('..')

from twisted.internet import reactor
from twisted.internet.protocol import DatagramProtocol
from twisted.internet.defer import Deferred
from twisted.internet.task import LoopingCall
from twisted.web.client import getPage
from twisted.web import static, server
from twisted.web.resource import Resource
from pyspades.site import get_servers
from pyspades.tools import make_server_identifier
import json
import jinja2
import urllib

UPDATE_INTERVAL = 10
PYSPADES_TIMEOUT = 2
INPUT = 'in.html'

SITE = 'http://ace-spades.com/forums/ucp.php?mode=login'

from twisted.python import log

def got_user(data, name):
    result = bool(data.count('You have been successfully logged in.'))
    print 'Auth for %s -> %s' % (name, result)
    return result

def check_user(name, password):
    return getPage(SITE, method='POST', 
        postdata = urllib.urlencode(
            {'username' : name, 'password' : password, 'login' : 'Login'}
        ),
        headers = {'Content-Type' : 'application/x-www-form-urlencoded'}
        ).addCallback(got_user, name).addErrback(log.err)

from feature_server.statistics import (StatsFactory, StatsServer,
    DEFAULT_PORT)

class SiteStatisticsProtocol(StatsServer):
    def connection_accepted(self):
        print 'Statistics client %s (%s) connected.' % (self.name,
            self.transport.getPeer().host)
    
    def add_kill(self, name):
        self.factory.get_user(name)['kills'] += 1
        self.factory.save()
    
    def add_death(self, name):
        self.factory.get_user(name)['deaths'] += 1
        self.factory.save()
    
    def check_user(self, name, password):
        print 'Checking auth for %s' % name
        return check_user(name, password)

class SiteStatisticsFactory(StatsFactory):
    protocol = SiteStatisticsProtocol
    
    def __init__(self, *arg, **kw):
        StatsFactory.__init__(self, *arg, **kw)
        try:
            self.users = json.load(open('users.txt', 'rb'))
        except IOError:
            self.users = {}
    
    def get_user(self, name):
        key = name.lower()
        if key not in self.users:
            self.users[key] = {
                'name' : name,
                'kills' : 0,
                'deaths' : 0
            }
        return self.users[key]

    def get_highscores(self):
        return sorted(self.users.iteritems(), 
            key = lambda x: x[1]['kills'], reverse = True)
    
    def save(self):
        json.dump(self.users, open('users.txt', 'wb'))

class QueryProtocol(DatagramProtocol):
    pyspades_set = None
    saved_pyspades = None
    def startProtocol(self):
        self.saved_pyspades = set()
        self.pyspades_numbers = []
        self.servers = []
        self.update()
    
    def save(self, servers):
        self.saved_pyspades = self.pyspades_set or set()
        self.pyspades_numbers = self.saved_pyspades.copy()
        self.servers = servers
        self.pyspades_set = None
    
    def got_servers(self, servers):
        self.pyspades_set = set()
        for server in servers:
            self.transport.write('HELLO', (server.ip, 32887))
        reactor.callLater(PYSPADES_TIMEOUT, self.save, servers)
    
    def update(self):
        get_servers().addCallback(self.got_servers)
        reactor.callLater(UPDATE_INTERVAL, self.update)
    
    def datagramReceived(self, data, address):
        if self.pyspades_set is None or data != 'HI':
            return
        self.pyspades_set.add(make_server_identifier(address[0], address[1]))

class MainResource(Resource):
    def __init__(self, root):
        self.query = QueryProtocol()
        reactor.listenUDP(0, self.query)
        if stats_pass is not None:
            self.statistics = SiteStatisticsFactory(stats_pass)
            reactor.listenTCP(DEFAULT_PORT, self.statistics)
        env = jinja2.Environment(loader = jinja2.PackageLoader('web'),
            autoescape = True)
        self.template = env.get_template(INPUT)
        Resource.__init__(self)
    
    def render_GET(self, request):
        query = self.query
        data = str(self.template.render(
            protocol = query, 
            servers = query.servers,
            has_pyspades = query.saved_pyspades, 
            make_server_identifier = make_server_identifier,
            statistics = self.statistics)
        )
        return data
        
class CommonResource(Resource):
    def __init__(self, main):
        self.main = main
        Resource.__init__(self)

class ListResource(CommonResource):
    def render_GET(self, request):
        return '\n'.join(self.main.query.pyspades_numbers)

root = Resource()
main = MainResource(root)
root.putChild('', main)
root.putChild('list', ListResource(main))
root.putChild('style.css', static.File('style.css'))
site = server.Site(root)
reactor.listenTCP(port, site)

reactor.run()