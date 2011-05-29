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
    
    def __init__(self):
        self.ops = []
        self.voices = []
    
    def _get_nickname(self):
        return self.factory.nickname
    nickname = property(_get_nickname)
    
    def signedOn(self):
        self.join(self.factory.channel)
    
    def joined(self, channel):
        print "Joined channel %s" % channel
    
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
        print modes, args
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
        if user in self.ops or user in self.voices:
            max_size = MAX_IRC_CHAT_SIZE - len(self.protocol.server_prefix) - 1
            message = ("<%s> %s" % (('@' if user in self.ops else '+') + user, msg))[:max_size]
            self.factory.server.log(message)
            self.factory.server.send_chat(message)
    
    @channel
    def userLeft(self, user, channel):
        if user in self.ops:
            self.ops.remove(user)
        if user in self.voices:
            self.voices.remove(user)
    
    def send(self, msg):
        self.msg(self.factory.channel, msg)
    
    def me(self, msg):
        self.me(self.factory.channel, msg)

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
        self.factory.bot.me(msg)
