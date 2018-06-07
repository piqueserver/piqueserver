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

import json

from twisted.internet.protocol import (ReconnectingClientFactory,
                                       ServerFactory)
from twisted.internet import reactor
from twisted.internet.defer import Deferred, succeed
from twisted.protocols.basic import Int16StringReceiver

CONNECTION_TIMEOUT = 5
DEFAULT_PORT = 32880


def hash_password(value):
    return value  # hashlib.md5(value).hexdigest()


class StatsProtocol(Int16StringReceiver):

    def stringReceived(self, data):
        self.object_received(json.loads(data.decode()))

    def send_object(self, obj):
        if self.transport is not None:
            self.sendString(json.dumps(obj).encode())

    def object_received(self, obj):
        pass


class StatsServer(StatsProtocol):

    # TODO: add __init__ method for defined attributes and don't forget to call
    # super
    # pylint: disable=attribute-defined-outside-init

    def connectionMade(self):
        self.timeout_call = reactor.callLater(CONNECTION_TIMEOUT,
                                              self.timed_out)

    # TODO: check why the below
    # pylint: disable=signature-differs
    def connectionLost(self, reason):
        if self in self.factory.connections:
            self.factory.connections.remove(self)

    def object_received(self, obj):
        obj_type = obj.get('type', None)
        if self.timeout_call is not None:
            if obj_type != 'auth':
                self.transport.loseConnection()
                return
            password = obj['password']
            if password != self.factory.password:
                self.transport.loseConnection()
            else:
                self.timeout_call.cancel()
                self.timeout_call = None
                self.send_object({'type': 'authed'})
                self.name = obj['name']
                self.factory.connections.append(self)
                self.connection_accepted()
            return
        if obj_type == 'kill':
            self.add_kill(obj['name'])
        elif obj_type == 'death':
            self.add_death(obj['name'])
        elif obj_type == 'login':
            # TODO: do we want to be returning the result?
            # pylint: disable=unused-variable
            result = self.check_user(obj['name'], obj['password']).addCallback(
                self.send_login_result)

    def send_login_result(self, result):
        self.send_object({'type': 'login', 'result': result})

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
        self.send_object({'type': 'auth', 'name': self.factory.name,
                          'password': self.factory.password})

    def object_received(self, obj):
        obj_type = obj['type']
        if obj_type == 'authed':
            self.factory.callback(self)
        elif obj_type == 'login':
            defer = self.login_defers.pop(0)
            defer.callback(obj['result'])

    def add_kill(self, name):
        self.send_object({'type': 'kill', 'name': name})

    def add_death(self, name):
        self.send_object({'type': 'death', 'name': name})

    def login_user(self, name, password):
        defer = Deferred()
        password = hash_password(password)
        self.send_object({'type': 'login', 'name': name,
                          'password': password})
        self.login_defers.append(defer)
        return defer


class StatsClientFactory(ReconnectingClientFactory):
    protocol = StatsClient
    maxDelay = 20

    def __init__(self, name, password, callback):
        self.name = name
        self.password = hash_password(password)
        self.callback = callback


def connect_statistics(host, port, name, password, callback, interface=''):
    reactor.connectTCP(host, port, StatsClientFactory(name, password, callback),
                       bindAddress=(interface, 0))

if __name__ == '__main__':
    class TestServer(StatsServer):

        def add_kill(self, name):
            print('Adding kill to', name)

        def add_death(self, name):
            print('Adding death to', name)

        def check_user(self, name, password):
            print('Checking user name/pass ({}, {})'.format(name, password))
            # TODO: pylint thinks this function should have an argument
            #       check it out
            return succeed()  # pylint: disable=no-value-for-parameter

    class TestFactory(StatsFactory):
        protocol = TestServer

    reactor.listenTCP(DEFAULT_PORT, TestFactory('marmelade'))
    reactor.run()
