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

import re
import random
from itertools import groupby, chain
from operator import attrgetter
from typing import List

from twisted.words.protocols import irc
from twisted.internet import reactor, protocol
from twisted.logger import Logger

from pyspades.constants import MAX_CHAT_SIZE
from pyspades.common import encode, escape_control_codes
from pyspades.types import AttributeSet
from piqueserver import commands
from piqueserver.commands import command, restrict


MAX_IRC_CHAT_SIZE = MAX_CHAT_SIZE * 2
IRC_TEAM_COLORS = {0: '\x0302', 1: '\x0303'}
SPLIT_WHO_IN_TEAMS = True
SPLIT_THRESHOLD = 20  # players

irc_color_codes = re.compile(r"\x03(?:\d{1,2}(?:,\d{1,2})?)?", re.UNICODE)

log = Logger()

def channel(func):
    """This decorator rewrites the username of incoming messages to strip the
    ident and rejects it if the source channel is not equal to the channel the
    bot is in"""
    def new_func(self, user, irc_channel, *arg, **kw):
        if not irc_channel.lower() == self.factory.channel:
            return
        user = user.split('!', 1)[0]
        func(self, user, irc_channel, *arg, **kw)
    return new_func


class IRCBot(irc.IRCClient):
    ops = None
    voices = None
    unaliased_name = None
    name = None

    @property
    def nickname(self):
        return self.factory.nickname

    @nickname.setter
    def nickname(self, nickname):
        self.factory.nickname = nickname

    @property
    def colors(self):
        return self.factory.colors

    @colors.setter
    def colors(self, colors):
        self.factory.colors = colors

    @property
    def admin(self):
        return self.factory.admin

    @property
    def user_types(self):
        return self.factory.user_types

    @property
    def rights(self):
        return self.factory.rights

    def signedOn(self):
        self.join(self.factory.channel, self.factory.password)

    def joined(self, irc_channel):
        if irc_channel.lower() == self.factory.channel:
            self.ops = set()
            self.voices = set()
        log.info("Joined channel %s" % irc_channel)

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
            # reset ops or voices in case not previously set (they should be in
            # the joined method, but joined() not observed to always get called)
            if not self.ops: self.ops = set()
            if not self.voices: self.voices = set()
            l = {'@': self.ops, '+': self.voices}
            if mode in l:
                l[mode].add(name[1:])

    def left(self, irc_channel):
        if irc_channel.lower() == self.factory.channel:
            self.ops = None
            self.voices = None

    @channel
    def modeChanged(self, user, irc_channel, set_something, modes, args):
        ll = {'o': self.ops, 'v': self.voices}
        for i in range(len(args)):
            mode, name = modes[i], args[i]
            if mode not in ll:
                continue
            l = ll[mode]
            if set_something:
                l.add(name)
            elif not set_something:
                l.discard(name)

    @channel
    def privmsg(self, user, irc_channel, msg):
        if user not in self.ops and user not in self.voices:
            return  # This user is unpriviledged

        prefix = '@' if user in self.ops else '+'
        alias = self.factory.aliases.get(user, user)

        if msg.startswith(self.factory.chatprefix):
            max_len = MAX_IRC_CHAT_SIZE - \
                len(self.protocol.server_prefix) - 1
            msg = msg[len(self.factory.chatprefix):].strip()
            message = ("[irc] <{}> {}".format(prefix + alias, msg))[:max_len]
            log.info(escape_control_codes(message))
            self.factory.server.broadcast_chat(message)
        elif msg.startswith(self.factory.commandprefix) and user in self.ops:
            self.unaliased_name = user
            self.name = prefix + alias
            user_input = msg[len(self.factory.commandprefix):]
            result = commands.handle_input(self, user_input)
            if result is not None:
                self.send("{}: {}".format(user, result))

    @channel
    def userLeft(self, user, irc_channel):
        self.ops.discard(user)
        self.voices.discard(user)

    def userQuit(self, user, message):
        self.userLeft(user, self.factory.channel)

    def userKicked(self, kickee, irc_channel, kicker, message):
        self.userLeft(kickee, irc_channel)

    def send(self, msg, do_filter=False):
        if do_filter:
            msg = irc_color_codes.sub('', msg)
        self.msg(self.factory.channel, msg)

    def me(self, msg, do_filter=False):
        if do_filter:
            msg = irc_color_codes.sub('', msg)
        self.describe(self.factory.channel, msg)

    # methods used to emulate the behaviour of regular Connection objects to
    # prevent errors when command writers didn't test that their commands would
    # work when run from IRC
    def send_chat(self, value: str, _):
        self.send(value)

    def send_lines(self, lines: List[str]):
        self.send("\n".join(lines))

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
            self.rights.update(commands.get_rights(user_type))
        self.server = server
        self.nickname = config.get('nickname',
                                   'piqueserver%s' % random.randrange(0, 99))
        self.username = config.get('username', 'piqueserver')
        self.realname = config.get('realname', server.name)
        self.channel = config.get('channel', "#piqueserver.bots").lower()
        self.commandprefix = config.get('commandprefix', '.')
        self.chatprefix = config.get('chatprefix', '')
        self.password = config.get('password', '') or None

    def startedConnecting(self, connector):
        log.info("Connecting to IRC server...")

    def clientConnectionLost(self, connector, reason):
        log.info("Lost connection to IRC server ({}), reconnecting in {} seconds".format(
            reason, self.lost_reconnect_delay))
        reactor.callLater(self.lost_reconnect_delay, connector.connect)

    def clientConnectionFailed(self, connector, reason):
        log.info("Could not connect to IRC server ({}), retrying in {} seconds".format(
            reason, self.failed_reconnect_delay))
        reactor.callLater(self.failed_reconnect_delay, connector.connect)

    def buildProtocol(self, address):
        p = self.protocol()
        p.factory = self
        p.protocol = self.server
        self.bot = p
        return p


class IRCRelay:
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
    return '{} #{}'.format(player.name, player.player_id)


def format_name_color(player):
    return (IRC_TEAM_COLORS.get(player.team.id, '') +
            '{} #{}'.format(player.name, player.player_id))


@restrict("irc")
@command()
def who(connection):
    protocol = connection.protocol
    player_count = len(protocol.players)
    if player_count == 0:
        connection.me('has no players connected')
        return
    sorted_players = sorted(protocol.players.values(),
                            key=attrgetter('team.id', 'name'))
    name_formatter = format_name_color if connection.colors else format_name
    teams = []
    formatted_names = []
    for k, g in groupby(sorted_players, attrgetter('team')):
        teams.append(k)
        formatted_names.append(map(name_formatter, g))
    separator = '\x0f, ' if connection.colors else ', '
    if not SPLIT_WHO_IN_TEAMS or player_count < SPLIT_THRESHOLD:
        noun = 'player' if player_count == 1 else 'players'
        msg = 'has {} {} connected: '.format(player_count, noun)
        msg += separator.join(chain.from_iterable(formatted_names))
        connection.me(msg)
    else:
        for team, names in zip(teams, formatted_names):
            name_count = len(names)
            noun = 'player' if name_count == 1 else 'players'
            msg = 'has {} {} in {}: '.format(name_count, noun, team.name)
            msg += separator.join(names)
            connection.me(msg)


@restrict("irc")
@command()
def score(connection):
    connection.me("scores: Blue {} - Green {}".format(
        connection.protocol.blue_team.score,
        connection.protocol.green_team.score))


@restrict("irc")
@command()
def alias(connection, value=None):
    aliases = connection.factory.aliases
    unaliased_name = connection.unaliased_name
    if value is None:
        alias = aliases.get(unaliased_name)
        if alias:
            message = 'aliases {} to {}'.format(unaliased_name, alias)
        else:
            message = "doesn't have an alias for %s" % unaliased_name
    else:
        aliases[unaliased_name] = value
        message = 'will alias {} to {}'.format(unaliased_name, value)
    connection.me(message)


@restrict("irc")
@command()
def unalias(connection):
    aliases = connection.factory.aliases
    unaliased_name = connection.unaliased_name
    if unaliased_name in aliases:
        aliases.pop(unaliased_name)
        message = 'will no longer alias %s' % unaliased_name
    else:
        message = "doesn't have an alias for %s" % unaliased_name
    connection.me(message)


@restrict("irc")
@command()
def colors(connection):
    connection.colors = not connection.colors
    if connection.colors:
        return '\x0312c\x0304o\x0309l\x0308o\x0306r\x0313s \x0f\x16ON!'
    else:
        return 'colors off'
