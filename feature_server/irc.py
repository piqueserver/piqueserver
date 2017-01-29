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

from twisted.words.protocols import irc
from twisted.internet import reactor, protocol
from pyspades.constants import MAX_CHAT_SIZE
from pyspades.common import encode, decode
from pyspades.types import AttributeSet
import commands

import random
import string
from itertools import groupby, chain, izip
from operator import attrgetter

MAX_IRC_CHAT_SIZE = MAX_CHAT_SIZE * 2
PRINTABLE_CHARACTERS = ('0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOP'
                        'QRSTUVWXYZ!"#$%&\\\'()*+,-./:;<=>?@[\\]^_`{|}~ \t')
IRC_TEAM_COLORS = {0 : '\x0302', 1 : '\x0303'}
SPLIT_WHO_IN_TEAMS = True
SPLIT_THRESHOLD = 20 # players

def is_printable(value):
    return value in PRINTABLE_CHARACTERS

def filter_printable(value):
    return filter(is_printable, value)

def channel(func):
    def new_func(self, user, channel, *arg, **kw):
        if not channel.lower() == self.factory.channel:
            return
        user = user.split('!', 1)[0]
        func(self, user, channel, *arg, **kw)
    return new_func

class IRCBot(irc.IRCClient):
    ops = None
    voices = None
    unaliased_name = None

    def _get_nickname(self):
        return self.factory.nickname
    nickname = property(_get_nickname)

    def _get_colors(self):
        return self.factory.colors
    colors = property(_get_colors)

    def _get_admin(self):
        return self.factory.admin
    admin = property(_get_admin)

    def _get_user_types(self):
        return self.factory.user_types
    user_types = property(_get_user_types)

    def _get_rights(self):
        return self.factory.rights
    rights = property(_get_rights)

    def signedOn(self):
        self.join(self.factory.channel, self.factory.password)

    def joined(self, channel):
        if channel.lower() == self.factory.channel:
            self.ops = set()
            self.voices = set()
        print "Joined channel %s" % channel

    def irc_NICK(self, prefix, params):
        user = prefix.split('!', 1)[0]
        new_user = params[0]
        if user in self.ops:
            self.ops.discard(user)
            self.ops.add(new_user)
        if user in self.voices:
            self.voices.discard(user)
            self.voices.add(new_user)

    def irc_RPL_NAMREPLY(self, *arg):
        if not arg[1][2].lower() == self.factory.channel:
            return
        for name in arg[1][3].split():
            mode = name[0]
            l = {'@': self.ops, '+': self.voices}
            if mode in l:
                l[mode].add(name[1:])

    def left(self, channel):
        if channel.lower() == self.factory.channel:
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
            if set:
                l.add(name)
            elif not set:
                l.discard(name)

    @channel
    def privmsg(self, user, channel, msg):
        if user in self.ops or user in self.voices:
            prefix = '@' if user in self.ops else '+'
            alias = self.factory.aliases.get(user, user)
            if msg.startswith(self.factory.commandprefix) and user in self.ops:
                self.unaliased_name = user
                self.name = prefix + alias
                input = msg[len(self.factory.commandprefix):]
                result = commands.handle_input(self, input)
                if result is not None:
                    self.send("%s: %s" % (user, result))
            elif msg.startswith(self.factory.chatprefix):
                max_len = MAX_IRC_CHAT_SIZE - len(self.protocol.server_prefix) - 1
                msg = msg[len(self.factory.chatprefix):].strip()
                message = ("<%s> %s" % (prefix + alias, msg))[:max_len]
                message = message.decode('cp1252')
                print message.encode('ascii', 'replace')
                self.factory.server.send_chat(encode(message))

    @channel
    def userLeft(self, user, channel):
        self.ops.discard(user)
        self.voices.discard(user)

    def userQuit(self, user, message):
        self.userLeft(user, self.factory.channel)

    def userKicked(self, kickee, channel, kicker, message):
        self.userLeft(kickee, channel)

    def send(self, msg, filter = False):
        msg = msg.encode('cp1252', 'replace')
        if filter:
            msg = filter_printable(msg)
        self.msg(self.factory.channel, msg)

    def me(self, msg, filter = False):
        msg = msg.encode('cp1252', 'replace')
        if filter:
            msg = filter_printable(msg)
        self.describe(self.factory.channel, msg)

class IRCClientFactory(protocol.ClientFactory):
    protocol = IRCBot
    lost_reconnect_delay = 20
    failed_reconnect_delay = 60
    bot = None
    aliases = None
    colors = True
    admin = None
    user_types = None
    rights = None

    def __init__(self, server, config):
        self.aliases = {}
        self.admin = True
        self.user_types = AttributeSet(['admin', 'irc'])
        self.rights = AttributeSet()
        for user_type in self.user_types:
            self.rights.update(commands.rights.get(user_type, ()))
        self.server = server
        self.nickname = config.get('nickname',
            'pyspades%s' % random.randrange(0, 99)).encode('ascii')
        self.username = config.get('username', 'pyspades').encode('ascii')
        self.realname = config.get('realname', server.name).encode('ascii')
        self.channel = config.get('channel', "#pyspades.bots").encode(
            'ascii').lower()
        self.commandprefix = config.get('commandprefix', '.').encode('ascii')
        self.chatprefix = config.get('chatprefix', '').encode('ascii')
        self.password = config.get('password', '').encode('ascii') or None

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
        protocol.connectTCP(config.get('server'), config.get('port', 6667),
            self.factory)

    def send(self, *arg, **kw):
        if self.factory.bot is None:
            return
        self.factory.bot.send(*arg, **kw)

    def me(self, *arg, **kw):
        if self.factory.bot is None:
            return
        self.factory.bot.me(*arg, **kw)

def format_name(player):
    return '%s #%s' % (player.name, player.player_id)

def format_name_color(player):
    return (IRC_TEAM_COLORS.get(player.team.id, '') +
        '%s #%s' % (player.name, player.player_id))

def irc(func):
    return commands.restrict(func, ('irc',))

@irc
def who(connection):
    protocol = connection.protocol
    player_count = len(protocol.players)
    if player_count == 0:
        connection.me('has no players connected')
        return
    sorted_players = sorted(protocol.players.values(),
        key = attrgetter('team.id', 'name'))
    name_formatter = format_name_color if connection.colors else format_name
    teams = []
    formatted_names = []
    for k, g in groupby(sorted_players, attrgetter('team')):
        teams.append(k)
        formatted_names.append(map(name_formatter, g))
    separator = '\x0f, ' if connection.colors else ', '
    if not SPLIT_WHO_IN_TEAMS or player_count < SPLIT_THRESHOLD:
        noun = 'player' if player_count == 1 else 'players'
        msg = 'has %s %s connected: ' % (player_count, noun)
        msg += separator.join(chain.from_iterable(formatted_names))
        connection.me(msg)
    else:
        for team, names in izip(teams, formatted_names):
            name_count = len(names)
            noun = 'player' if name_count == 1 else 'players'
            msg = 'has %s %s in %s: ' % (name_count, noun, team.name)
            msg += separator.join(names)
            connection.me(msg)

@irc
def score(connection):
    connection.me("scores: Blue %s - Green %s" % (
        connection.protocol.blue_team.score,
        connection.protocol.green_team.score))

@irc
def alias(connection, value = None):
    aliases = connection.factory.aliases
    unaliased_name = connection.unaliased_name
    if value is None:
        alias = aliases.get(unaliased_name)
        if alias:
            message = 'aliases %s to %s' % (unaliased_name, alias)
        else:
            message = "doesn't have an alias for %s" % unaliased_name
    else:
        aliases[unaliased_name] = value
        message = 'will alias %s to %s' % (unaliased_name, value)
    connection.me(message)

@irc
def unalias(connection):
    aliases = connection.factory.aliases
    unaliased_name = connection.unaliased_name
    if unaliased_name in aliases:
        aliases.pop(unaliased_name)
        message = 'will no longer alias %s' % unaliased_name
    else:
        message = "doesn't have an alias for %s" % unaliased_name
    connection.me(message)

@irc
def colors(connection):
    connection.colors = not connection.colors
    if connection.colors:
        return '\x0312c\x0304o\x0309l\x0308o\x0306r\x0313s \x0f\x16ON!'
    else:
        return 'colors off'

for func in (who, score, alias, unalias, colors):
    commands.add(func)
