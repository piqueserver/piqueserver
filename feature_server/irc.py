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

class IRCBot(irc.IRCClient):
    ops = []
    voices = []
    
    def _get_nickname(self):
	return self.factory.nickname
    nickname = property(_get_nickname)
    
    def signedOn(self):
        self.join(self.factory.channel)
    
    def joined(self, channel):
        print "Joined channel %s" % channel
    
    def irc_RPL_NAMREPLY(self, *nargs):
	if not nargs[1][2] == self.factory.channel:
	    return
	for name in nargs[1][3].split():
	    mode = name[0]
	    l = {'@':self.ops, '+':self.voices}
	    if mode in l: l[mode].append(name[1:])
    
    def channel(func):
	def new_func(self, user, channel, *arg, **kw):
	    if not channel == self.factory.channel:
		return
	    user = user.split('!', 1)[0]
	    func(self, user, channel, *arg, **kw)
	new_func.func_name = func.func_name
	return new_func
    
    def left(self, channel):
	if channel == self.factory.channel:
	    del ops[:]
	    del voices[:]
    
    @channel
    def modeChanged(self, user, channel, set, modes, args):
	l = {'o':self.ops, 'v':self.voices}
	if not modes in l:
	    return
	l = l[modes]
	target = args[0]
	if target not in l and set:
	    l.append(target)
	elif target in l and not set:
	    l.remove(target)
    
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
	    del self.ops[user]
	if user in self.voices:
	    del self.voices[user]
    
    def send(self, msg):
	self.msg(self.factory.channel, msg)
    
    def me(self, msg):
	self.me(self.factory.channel, msg)

class IRCClientFactory(protocol.ClientFactory):
    protocol = IRCBot
    connectionLostReconnectDelay = 20
    connectionFailedReconnectDelay = 60
    bot = None
    
    def __init__(self, server, config):
	self.server = server
        self.nickname = config.get('nickname', 'pyspades%s' % random.randrange(0,99)).encode('ascii')
	self.username = config.get('username', 'pyspades').encode('ascii')
	self.realname = config.get('realname', server.name).encode('ascii')
	self.channel = config.get('channel', "#pyspades.bots").encode('ascii')
	
    def startedConnecting(self, connector):
	print "Connecting to IRC server..."
    
    def clientConnectionLost(self, connector, reason):
        print "Lost connection to IRC server (%s), reconnecting in %s seconds" % (reason, self.connectionLostReconnectDelay)
	reactor.callLater(self.connectionLostReconnectDelay, connector.connect)
    
    def clientConnectionFailed(self, connector, reason):
        print "Could not connect to IRC server (%s), retrying in %s seconds" % (reason, self.connectionFailedReconnectDelay)
	reactor.callLater(self.connectionFailedReconnectDelay, connector.connect)
    
    def buildProtocol(self, address):
	p = self.protocol()
	p.factory = self
	self.bot = p
	return p

class IRCRelay(object):
    factory = None
    
    def __init__(self, server, config):
        self.factory = IRCClientFactory(server, config)
        reactor.connectTCP(config.get('server'), config.get('port', 6667), self.factory)
    
    def send(self, msg):
	try:
	    self.factory.bot.send(msg)
	except:
	    return
    
    def me(self, msg):
	try:
	    self.factory.bot.me(msg)
	except:
	    return
