# Copyright (c) Mathias Kaerlev 2011.

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
    raise SystemExit('usage: %s <output html path> [stats pass]' % sys.argv[0])

path = args[0]
if len(args) == 2:
    stats_pass = args[1]
else:
    stats_pass = None
OUTPUT = os.path.join(path, 'index.html')
PYSPADES_LIST_FILE = os.path.join(path, 'list')

sys.path.append('..')

from twisted.internet import reactor
from twisted.internet.protocol import DatagramProtocol
from twisted.internet.defer import Deferred
from twisted.internet.task import LoopingCall
from pyspades.site import get_servers
from pyspades.tools import make_server_number
import json
import jinja2

UPDATE_INTERVAL = 10
PYSPADES_TIMEOUT = 2
INPUT = 'in.html'

import urllib
from twisted.web.client import getPage

SITE = 'http://ace-spades.com/forums/bb-login.php'

from twisted.python import log

def got_user(data, name):
    result = data.count('Log in Failed') == 0
    print 'Auth for %s -> %s' % (name, result)
    return result

def check_user(name, password):
    return getPage(SITE, method='POST', 
        postdata = urllib.urlencode(
            {'user_login' : name, 'password' : password}
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
    
    def save(self):
        json.dump(self.users, open('users.txt', 'wb'))

class QueryProtocol(DatagramProtocol):
    pyspades_set = None
    statistics = None
    def startProtocol(self):
        if stats_pass is not None:
            self.statistics = SiteStatisticsFactory(stats_pass)
            reactor.listenTCP(DEFAULT_PORT, self.statistics)
        env = jinja2.Environment(loader = jinja2.PackageLoader('web'))
        self.template = env.get_template(INPUT)
        self.update()
    
    def write_html(self, servers):
        pyspades_set = self.pyspades_set or set()
        pyspades_numbers = [str(make_server_number(item)) for item in
            pyspades_set]
        open(PYSPADES_LIST_FILE, 'wb').write('\n'.join(pyspades_numbers))
        data = str(self.template.render(protocol = self, servers = servers,
            has_pyspades = pyspades_set, 
            make_server_number = make_server_number))
        open(OUTPUT, 'wb').write(data)
        self.pyspades_set = None
    
    def get_highscores(self):
        return sorted(self.statistics.users.iteritems(), 
            key = lambda x: x[1]['kills'], reverse = True)
    
    def got_servers(self, servers):
        self.pyspades_set = set()
        for server in servers:
            self.transport.write('HELLO', (server.ip, 32887))
        reactor.callLater(PYSPADES_TIMEOUT, self.write_html, servers)
    
    def update(self):
        get_servers().addCallback(self.got_servers)
        reactor.callLater(UPDATE_INTERVAL, self.update)
    
    def datagramReceived(self, data, address):
        if self.pyspades_set is None or data != 'HI':
            return
        self.pyspades_set.add(address[0])
    
reactor.listenUDP(0, QueryProtocol())

reactor.run()