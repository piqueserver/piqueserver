"""
Kicks a player if inactive for too long.

Maintainer: hompy
"""

from math import ceil
from operator import attrgetter
from twisted.internet import reactor
from pyspades.common import prettify_timespan
from commands import name, get_player, add, admin

S_AFK_CHECK = '{player} has been inactive for {time}'
S_NO_PLAYERS_INACTIVE = 'No players or connections inactive for {time}'
S_AFK_KICKED = ('{num_players} players kicked, {num_connections} connections '
    'terminated for {time} inactivity')
S_AFK_KICK_REASON = 'Inactive for {time}'

def afk(connection, player):
    player = get_player(connection.protocol, player)
    elapsed = prettify_timespan(reactor.seconds() - player.last_activity, True)
    return S_AFK_CHECK.format(player = player.name, time = elapsed)

@name('kickafk')
@admin
def kick_afk(connection, minutes, amount = None):
    protocol = connection.protocol
    minutes = int(minutes)
    if minutes < 1:
        raise ValueError()
    to_kick = []
    seconds = minutes * 60.0
    minutes_s = prettify_timespan(seconds)
    lower_bound = reactor.seconds() - seconds
    for conn in protocol.connections.values():
        if not conn.admin and conn.last_activity < lower_bound:
            to_kick.append(conn)
    if not to_kick:
        return S_NO_PLAYERS_INACTIVE.format(time = minutes_s)
    to_kick.sort(key = attrgetter('last_activity'))
    to_kick.sort(key = lambda conn: conn.name is None)
    amount = amount or len(to_kick)
    kicks = 0
    for conn in to_kick[:amount]:
        if conn.name:
            conn.afk_kick()
            kicks += 1
        else:
            conn.disconnect()
    message = S_AFK_KICKED.format(num_players = kicks,
        num_connections = amount - kicks, time = minutes_s)
    protocol.irc_say('* ' + message)
    if connection in protocol.players:
        return message

add(afk)
add(kick_afk)

def apply_script(protocol, connection, config):
    time_limit = config.get('afk_time_limit', None)
    time_limit = time_limit and time_limit * 60.0

    class AFKConnection(connection):
        afk_kick_call = None
        last_activity = None

        def afk_kick(self):
            if self.name:
                time_inactive = reactor.seconds() - self.last_activity
                time_inactive = max(1.0, round(time_inactive / 60.0)) * 60.0
                elapsed = prettify_timespan(time_inactive)
                self.kick(S_AFK_KICK_REASON.format(time = elapsed))
            else:
                self.disconnect()

        def reset_afk_kick_call(self):
            self.last_activity = reactor.seconds()
            if self.afk_kick_call and self.afk_kick_call.active():
                self.afk_kick_call.reset(time_limit)

        def on_disconnect(self):
            if self.afk_kick_call and self.afk_kick_call.active():
                self.afk_kick_call.cancel()
            self.afk_kick_call = None
            connection.on_disconnect(self)

        def on_user_login(self, user_type, verbose = True):
            if user_type in ('admin', 'trusted'):
                if self.afk_kick_call and self.afk_kick_call.active():
                    self.afk_kick_call.cancel()
                self.afk_kick_call = None
            return connection.on_user_login(self, user_type, verbose)

        def on_connect(self):
            if time_limit:
                self.afk_kick_call = reactor.callLater(time_limit, self.afk_kick)
            self.last_activity = reactor.seconds()
            return connection.on_connect(self)

        def on_chat(self, value, global_message):
            self.reset_afk_kick_call()
            return connection.on_chat(self, value, global_message)

        def on_orientation_update(self, x, y, z):
            self.reset_afk_kick_call()
            return connection.on_orientation_update(self, x, y, z)

    return protocol, AFKConnection
