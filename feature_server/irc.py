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
from commands import get_player, join_arguments, InvalidPlayer, InvalidTeam

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
                params = msg[len(self.factory.commandprefix):].split()
                result = handle_command(self, prefixed_username, params[0], params[1:])
                if result is not None:
                    self.send(result)
            else:
                max_len = MAX_IRC_CHAT_SIZE - len(self.protocol.server_prefix) - 1
                message = ("<%s> %s" % (prefixed_username, msg))[:max_len]
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

def admin(func):
    def new_func(bot, user, *arg, **kw):
        if not user[0] == '@':
            return
        func(bot, user, *arg, **kw)
    new_func.func_name = func.func_name
    return new_func

@admin
def mute(bot, user, value):
    player = get_player(bot.protocol, value)
    player.mute = True
    message = '%s has been muted by %s' % (player.name, user)
    bot.protocol.send_chat(message, irc = True)

@admin
def unmute(bot, user, value):
    player = get_player(bot.protocol, value)
    player.mute = False
    message = '%s has been unmuted by %s' % (player.name, user)
    bot.protocol.send_chat(message, irc = True)

@admin
def kick(bot, user, value, *arg):
    reason = join_arguments(arg)
    player = get_player(bot.protocol, value)
    player.kick(reason)

def who(bot, user):
    names = [conn.name for conn in bot.factory.server.players.values()]
    c = len(names)
    msg = "has %s player%s connected" % ( "no" if c == 0 else c,
        "" if c == 1 else "s" )
    if c > 0:
        msg += ": %s" % (', '.join(names))
    bot.me( msg )

command_list = [
    mute,
    unmute,
    kick,
    who
]

commands = {}

for command_func in command_list:
    commands[command_func.func_name] = command_func

def handle_command(bot, user, command, parameters):
    command = command.lower()
    try:
        command_func = commands[command]
    except KeyError:
        return #'Invalid command'
    try:
        return command_func(bot, user, *parameters)
    except TypeError:
        return '%s: Invalid number of arguments for %s' % (user[1:], command)
    except InvalidPlayer:
        return '%s: No such player' % user[1:]
    except InvalidTeam:
        return '%s: Invalid team specifier' % user[1:]
    except ValueError:
        return '%s: Invalid parameters' % user[1:]