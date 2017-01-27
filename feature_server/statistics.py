# feature_server/statistics.py
#
#   This file is licensed under the GNU General Public License version 3.
# In accordance to the license, there are instructions for obtaining the
# original source code. Furthermore, the changes made to this file can
# be seem by using diff tools and/or git-compatible software.
#
#   The license full text can be found in the "LICENSE" file, at the root
# of this repository. The original PySpades code can be found in this URL:
# https://github.com/infogulch/pyspades/releases/tag/v0.75.01.
#
# Original copyright: (C)2011-2012 Mathias Kaerlev
#

from twisted.internet.protocol import (Protocol, ReconnectingClientFactory,
    ServerFactory)
from twisted.internet import reactor
from twisted.internet.defer import Deferred, succeed
from twisted.protocols.basic import Int16StringReceiver
import json
import hashlib

CONNECTION_TIMEOUT = 5
DEFAULT_PORT = 32880

def hash_password(value):
    return value # hashlib.md5(value).hexdigest()

class StatsProtocol(Int16StringReceiver):
    def stringReceived(self, data):
        self.object_received(json.loads(data))

    def send_object(self, obj):
        if self.transport is not None:
            self.sendString(json.dumps(obj))

    def object_received(self, obj):
        pass

class StatsServer(StatsProtocol):
    def connectionMade(self):
        self.timeout_call = reactor.callLater(CONNECTION_TIMEOUT,
            self.timed_out)

    def connectionLost(self, reason):
        if self in self.factory.connections:
            self.factory.connections.remove(self)

    def object_received(self, obj):
        type = obj.get('type', None)
        if self.timeout_call is not None:
            if type != 'auth':
                self.transport.loseConnection()
                return
            password = obj['password']
            if password != self.factory.password:
                self.transport.loseConnection()
            else:
                self.timeout_call.cancel()
                self.timeout_call = None
                self.send_object({'type' : 'authed'})
                self.name = obj['name']
                self.factory.connections.append(self)
                self.connection_accepted()
            return
        if type == 'kill':
            self.add_kill(obj['name'])
        elif type == 'death':
            self.add_death(obj['name'])
        elif type == 'login':
            result = self.check_user(obj['name'], obj['password']).addCallback(
                self.send_login_result)

    def send_login_result(self, result):
        self.send_object({'type' : 'login', 'result' : result})

    def add_kill(self, name):
        pass

    def add_death(self, name):
        pass

    def check_user(self, name, password):
        pass

    def connection_accepted(self):
        pass

    def timed_out(self):
        self.timeout_call = None
        self.transport.loseConnection()

class StatsFactory(ServerFactory):
    protocol = StatsServer

    def __init__(self, password):
        self.password = hash_password(password)
        self.connections = []

class StatsClient(StatsProtocol):
    server = None
    login_defers = None

    def connectionMade(self):
        self.login_defers = []
        self.send_object({'type' : 'auth', 'name' : self.factory.name,
            'password' : self.factory.password})

    def object_received(self, obj):
        type = obj['type']
        if type == 'authed':
            self.factory.callback(self)
        elif type == 'login':
            defer = self.login_defers.pop(0)
            defer.callback(obj['result'])

    def add_kill(self, name):
        self.send_object({'type' : 'kill', 'name' : name})

    def add_death(self, name):
        self.send_object({'type' : 'death', 'name' : name})

    def login_user(self, name, password):
        defer = Deferred()
        password = hash_password(password)
        self.send_object({'type' : 'login', 'name' : name,
            'password' : password})
        self.login_defers.append(defer)
        return defer

class StatsClientFactory(ReconnectingClientFactory):
    protocol = StatsClient
    maxDelay = 20

    def __init__(self, name, password, callback):
        self.name = name
        self.password = hash_password(password)
        self.callback = callback

def connect_statistics(host, port, name, password, callback, interface = ''):
    reactor.connectTCP(host, port, StatsClientFactory(name, password, callback),
        bindAddress = (interface, 0))

if __name__ == '__main__':
    class TestServer(StatsServer):
        def add_kill(self, name):
            print 'Adding kill to', name

        def add_death(self, name):
            print 'Adding death to', name

        def check_user(self, name, password):
            print 'Checking user name/pass (%s, %s)' % (name, password)
            return succeed()

    class TestFactory(StatsFactory):
        protocol = TestServer

    reactor.listenTCP(DEFAULT_PORT, TestFactory('marmelade'))
    reactor.run()
