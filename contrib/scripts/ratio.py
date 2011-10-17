# KDR script because Enari said so  --GM

import commands

def ratio(connection):
    if connection not in connection.protocol.players:
        raise KeyError()
    if connection.deaths == 0:
        ratio_msg = "You have a kill-death ratio of %s" % (
            "0.00000" if connection.kills == 0 else "INFINITY")
    else:
        ratio = connection.kills/float(connection.deaths)
        ratio_msg = "You have a kill-death ratio of %.5f" % ratio
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
