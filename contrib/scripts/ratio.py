# KDR script because Enari said so  --GM

import commands

def ratio(connection, user=None):
    if user != None:
        connection = commands.get_player(connection.protocol, user)
    if connection not in connection.protocol.players:
        raise KeyError()
    ratio = connection.kills/float(max(1,connection.deaths))
    ratio_msg = "You have a kill-death ratio of %.2f" % ratio
    return ('%s (%s kills, %s deaths).' %
        (ratio_msg, connection.kills, connection.deaths))

commands.add(ratio)

def apply_script(protocol, connection, config):
    class RatioConnection(connection):
        deaths = 0
        
        def on_kill(self, killer):
            ret = connection.on_kill(self, killer)
            
            if ret:
                return ret
            
            self.deaths += 1
    
    return protocol, RatioConnection