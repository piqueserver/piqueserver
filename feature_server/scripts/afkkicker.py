from twisted.internet.task import LoopingCall

# Time in seconds
AFK_TIME_LIMIT = 600

def apply_script(protocol, connection, config):
    class AfkKickerProtocol(protocol):
        def __init__(self, *arg, **kw):
            protocol.__init__(self, *arg, **kw)
            self.afk_kicker_loop = LoopingCall(self.afk_kicker_update)
            self.afk_kicker_loop.start(AFK_TIME_LIMIT, False)
        
        def afk_kicker_update(self):
            k = []
            for player in self.players.values():
                if player.afk == True and player.admin == False:
                    k.append(player)
                player.afk = True
            for player in k:
                player.kick('Autokick: player was afk')        
    
    class AfkKickerConnection(connection):
        def on_connect(self, loader):
            self.afk = False
            return connection.on_connect(self, loader)

        def on_input_update(self):
            self.afk = False
            return connection.on_input_update(self)
    
    return AfkKickerProtocol, AfkKickerConnection