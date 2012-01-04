from twisted.internet import reactor
from pyspades.common import prettify_timespan
from commands import get_player, add

def afk(connection, player):
    player = get_player(connection.protocol, player)
    return '%s has been inactive for %s' % (player.name,
        prettify_timespan(reactor.seconds() - player.last_activity, True))

add(afk)

def apply_script(protocol, connection, config):
    time_limit = config.get('afk_time_limit', None)
    time_limit = time_limit and time_limit * 60.0
    kick_message = ('Inactive for %s' % prettify_timespan(time_limit) if
        time_limit else None)
    
    class AFKConnection(connection):
        afk_kick_call = None
        last_activity = None
        
        def on_user_login(self, user_type):
            if user_type == 'admin':
                self.afk_kick_call.cancel()
                self.afk_kick_call = None
            return connection.on_user_login(self, user_type)
        
        def on_connect(self):
            if time_limit:
                self.afk_kick_call = reactor.callLater(time_limit, self.kick,
                    kick_message)
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