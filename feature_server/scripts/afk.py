from math import ceil
from operator import attrgetter
from twisted.internet import reactor
from pyspades.common import prettify_timespan
from commands import name, get_player, add, admin

def afk(connection, player):
    player = get_player(connection.protocol, player)
    return '%s has been inactive for %s' % (player.name,
        prettify_timespan(reactor.seconds() - player.last_activity, True))

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
        return 'No players or connections inactive for %s' % minutes_s
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
    message = ('%s players kicked, %s connections terminated for %s '
        'inactivity' % (kicks, amount - kicks, minutes_s))
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
                self.kick('Inactive for %s' % prettify_timespan(time_inactive))
            else:
                self.disconnect()
        
        def on_disconnect(self):
            if self.afk_kick_call and self.afk_kick_call.active():
                self.afk_kick_call.cancel()
            self.afk_kick_call = None
            connection.on_disconnect(self)
        
        def on_user_login(self, user_type):
            if user_type == 'admin' and self.afk_kick_call:
                self.afk_kick_call.cancel()
                self.afk_kick_call = None
            return connection.on_user_login(self, user_type)
        
        def on_connect(self):
            if time_limit:
                self.afk_kick_call = reactor.callLater(time_limit, self.afk_kick)
            self.last_activity = reactor.seconds()
            return connection.on_connect(self)
        
        def on_chat(self, value, global_message):
            self.last_activity = reactor.seconds()
            if self.afk_kick_call:
                self.afk_kick_call.reset(time_limit)
            return connection.on_chat(self, value, global_message)
        
        def on_position_update(self):
            self.last_activity = reactor.seconds()
            if self.afk_kick_call:
                self.afk_kick_call.reset(time_limit)
            return connection.on_position_update(self)
    
    return protocol, AFKConnection