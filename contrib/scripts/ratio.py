# KDR script because Enari said so  --GM

import commands

def ratio(connection, user=None):
    if user != None:
        connection = commands.get_player(connection.protocol, user)
    if connection not in connection.protocol.players:
        raise KeyError()
    ratio = connection.ratio_kills/float(max(1,connection.ratio_deaths))
    ratio_msg = "You have a kill-death ratio of %.2f" % ratio
    return ('%s (%s kills, %s deaths).' %
        (ratio_msg, connection.ratio_kills, connection.ratio_deaths))

commands.add(ratio)

def apply_script(protocol, connection, config):
    class RatioConnection(connection):
        ratio_kills = 0
        ratio_deaths = 0
        
        def on_kill(self, killer):
            ret = connection.on_kill(self, killer)
            
            if ret:
                return ret
            
            if self != killer:
                killer.ratio_kills += 1
            
            self.ratio_deaths += 1
    
    return protocol, RatioConnection