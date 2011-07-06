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

from twisted.words.protocols import irc
from twisted.internet import reactor, protocol
from pyspades.constants import MAX_CHAT_SIZE
from pyspades.common import encode, decode
from commands import *

import random
import string

MAX_IRC_CHAT_SIZE = MAX_CHAT_SIZE * 2

def channel(func):
    def new_func(self, user, channel, *arg, **kw):
        if not channel == self.factory.channel:
            return
        user = user.split('!', 1)[0]
        func(self, user, channel, *arg, **kw)
    return new_func

class IRCBot(irc.IRCClient):
    ops = None
    voices = None
    colors = True
    
    def _get_nickname(self):
        return self.factory.nickname
    nickname = property(_get_nickname)
    
    def signedOn(self):
        self.join(self.factory.channel)
    
    def joined(self, channel):
        if channel == self.factory.channel:
            self.ops = []
            self.voices = []
        print "Joined channel %s" % channel
    
    def irc_NICK(self, prefix, params):
        user = prefix.split('!', 1)[0]
        new_user = params[0]
        if user in self.ops:
            self.ops.remove(user)
            self.ops.append(new_user)
        if user in self.voices:
            self.voices.remove(user)
            self.voices.append(new_user)
    
    def irc_RPL_NAMREPLY(self, *arg):
        if not arg[1][2] == self.factory.channel:
            return
        for name in arg[1][3].split():
            mode = name[0]
            l = {'@':self.ops, '+':self.voices}
            if mode in l: l[mode].append(name[1:])
    
    def left(self, channel):
        if channel == self.factory.channel:
            self.ops = None
            self.voices = None
    
    @channel
    def modeChanged(self, user, channel, set, modes, args):
        ll = {'o' : self.ops, 'v' : self.voices}
        for i in range(len(args)):
            mode, name = modes[i], args[i]
            if mode not in ll:
                continue
            l = ll[mode]
            if name not in l and set:
                l.append(name)
            elif name in l and not set:
                l.remove(name)
    
    @channel
    def privmsg(self, user, channel, msg):
        if (user in self.ops) or (user in self.voices):
            prefixed_username = ('@' if user in self.ops else '+') + user
            if msg.startswith(self.factory.commandprefix):
                self.admin = (user in self.ops)
                self.name = prefixed_username
                params = msg[len(self.factory.commandprefix):].split()
                result = handle_command(self, params[0], params[1:])
                if result is not None:
                    self.send("%s: %s" % (user, result))
            else:
                max_len = MAX_IRC_CHAT_SIZE - len(self.protocol.server_prefix) - 1
                message = ("<%s> %s" % (prefixed_username, msg))[:max_len]
                print message
                self.factory.server.send_chat(encode(message))
    
    @channel
    def userLeft(self, user, channel):
        if user in self.ops:
            self.ops.remove(user)
        if user in self.voices:
            self.voices.remove(user)
    
    def send(self, msg):
        msg = msg.encode('cp1252')
        self.msg(self.factory.channel, msg)
    
    def me(self, msg):
        msg = msg.encode('cp1252')
        self.describe(self.factory.channel, msg)

class IRCClientFactory(protocol.ClientFactory):
    protocol = IRCBot
    lost_reconnect_delay = 20
    failed_reconnect_delay = 60
    bot = None
    
    def __init__(self, server, config):
        self.server = server
        self.nickname = config.get('nickname', 
            'pyspades%s' % random.randrange(0, 99)).encode('ascii')
        self.username = config.get('username', 'pyspades').encode('ascii')
        self.realname = config.get('realname', server.name).encode('ascii')
        self.channel = config.get('channel', "#pyspades.bots").encode('ascii')
        self.commandprefix = config.get('commandprefix', '.').encode('ascii')
    
    def startedConnecting(self, connector):
        print "Connecting to IRC server..."
    
    def clientConnectionLost(self, connector, reason):
        print "Lost connection to IRC server (%s), reconnecting in %s seconds" % (
            reason, self.lost_reconnect_delay)
        reactor.callLater(self.lost_reconnect_delay, connector.connect)
    
    def clientConnectionFailed(self, connector, reason):
        print "Could not connect to IRC server (%s), retrying in %s seconds" % (
            reason, self.failed_reconnect_delay)
        reactor.callLater(self.failed_reconnect_delay, connector.connect)
    
    def buildProtocol(self, address):
        p = self.protocol()
        p.factory = self
        p.protocol = self.server
        self.bot = p
        return p

class IRCRelay(object):
    factory = None
    
    def __init__(self, protocol, config):
        self.factory = IRCClientFactory(protocol, config)
        reactor.connectTCP(config.get('server'), config.get('port', 6667),
            self.factory)
    
    def send(self, msg):
        self.factory.bot.send(msg)
    
    def me(self, msg):
        self.factory.bot.describe(msg)

def colors(connection):
    if connection in connection.protocol.players:
        raise KeyError()
    connection.colors = not connection.colors
    if connection.colors:
        return '12c04o09l08o06r13s 05ON!'
    else:
        return 'colors off'

def who(connection):
    if connection in connection.protocol.players:
        raise KeyError()
    if connection.colors:
        names = [('03' if conn.team.id else '02') + conn.name for conn in
            connection.protocol.players.values()]
    else:
        names = [conn.name for conn in connection.protocol.players.values()]
    count = len(names)
    msg = "has %s player%s connected" % ("no" if not count else count,
        "" if count == 1 else "s")
    if count:
        names.sort()
        msg += ": %s" % ((', ' if connection.colors else ', ').join(names))
    connection.me(msg)

def score(connection):
    if connection in connection.protocol.players:
        raise KeyError()
    connection.me("scores: Blue %s - Green %s" % (
        connection.protocol.blue_team.score,
        connection.protocol.green_team.score))

for func in (who, score, colors):
    add(func)