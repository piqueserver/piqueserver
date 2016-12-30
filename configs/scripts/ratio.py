"""
K/D ratio script.

Author: TheGrandmaster
Maintainer: mat^2
"""

from commands import get_player, add

# "ratio" must be AFTER "votekick" in the config.txt script list
RATIO_ON_VOTEKICK = True
IRC_ONLY = False

def ratio(connection, user=None):
    has_msg = "You have"
    if user != None:
        connection = get_player(connection.protocol, user)
        has_msg = "%s has"
        if connection not in connection.protocol.players:
            raise KeyError()
        has_msg %= connection.name
    if connection not in connection.protocol.players:
        raise KeyError()
    ratio = connection.ratio_kills/float(max(1,connection.ratio_deaths))
    ratio_msg = has_msg + (" a kill-death ratio of %.2f" % (ratio))
    return ('%s (%s kills, %s deaths).' %
        (ratio_msg, connection.ratio_kills, connection.ratio_deaths))

add(ratio)

def apply_script(protocol, connection, config):
    class RatioConnection(connection):
        ratio_kills = 0
        ratio_deaths = 0

        def on_kill(self, killer, type, grenade):
            if killer is not None and self.team is not killer.team:
                if self != killer:
                    killer.ratio_kills += 1
            self.ratio_deaths += 1
            return connection.on_kill(self, killer, type, grenade)

    class RatioProtocol(protocol):
        def on_votekick_start(self, instigator, victim, reason):
            result = protocol.on_votekick_start(self, instigator, victim, reason)
            if result is None and RATIO_ON_VOTEKICK:
                message = ratio(instigator, victim.name)
                if IRC_ONLY:
                    self.irc_say('* ' + message)
                else:
                    self.send_chat(message, irc = True)
            return result

    return RatioProtocol, RatioConnection
