# Script by Tocksman made for Goon Haven
# Short bit of documentation:
#
# This script will hopefully give server owners some control over what
# spectators do on there server. As of now since the release of v0.75,
# Goon Haven has had issues with spectators idling and using global chat
# to send information to a team so that they may know enemy positions
# or what the enemy is doing, etc. This script can block spectator chat
# as well as kick spectators after so much time as passed.
#
# Add these lines to your config:
# spectator_no_chat - This determines whether spectators can chat or not
#                     in your server. True disables chat. [True/False]
# spectator_kick - This determines whether spectators will be kicked after
#                  remaining for so long. True activates this. [True/False]
# spectator_kick_time - How long a spectator may remain before he is kicked.
#                       Time is in seconds. Note that setting time to 0
#                       will cause the script to deactivate or malfunction.
#
# Additionally, server owners who also give out "guard" or "mini-mod"
# positions can add the right "specpower" to the group rights in commands.py
# to have the guards/minimods be immune to the spectator kick and chat
# restrictions.
#
#
# Oh, and admins are also automatically immune to spectator kick and chat
# restrictions.
#
# Hope you enjoy!
# Tocksman

from math import ceil, floor
from twisted.internet import reactor

def apply_script(protocol, connection, config):
    spectator_no_chat = config.get('spectator_no_chat', False);
    spectator_kick = config.get('spectator_kick', False);
    spectator_kick_time = config.get('spectator_kick_time', 300); # in seconds

    class SpectatorControlConnection(connection):
        spec_check = None

        def on_chat(self, value, global_message):
            # if no chat is set and they're a spectator and not an admin
            # also, check for the right "specpower" for owners who add additional
            # rights such as guards, mini-mods, etc.
            if self.team.spectator and spectator_no_chat:
                if not self.admin and not self.rights.specpower: # not an admin
                    self.send_chat('Spectators cannot speak on this server.')
                    return False # deny
            return connection.on_chat(self, value, global_message)

        def on_team_join(self, team):
            if team.spectator and spectator_kick and spectator_kick_time > 0:
                if not self.admin and not self.rights.specpower: # not an admin
                    if self.spec_check is None or not self.spec_check.active(): # this check is necessary as you can join spectator from being a spectator
                        self.send_chat('Warning! Spectators are kicked after %s seconds!' % (spectator_kick_time))
                        time = ceil((spectator_kick_time / 4) * 3)
                        self.spec_check = reactor.callLater(time, self.check_spec_time, 1)
            elif not team.spectator:
                    if self.spec_check is not None and self.spec_check.active():
                        self.spec_check.cancel()
                        self.spec_check = None
            return connection.on_team_join(self, team)

        def on_disconnect(self):
            if self.spec_check is not None and self.spec_check.active():
                self.spec_check.cancel()
            self.spec_check = None
            return connection.on_disconnect(self)

        def check_spec_time(self, id):
            if not self.team.spectator:
                print 'WARNING 1. Safety check kept an non-spectator from being spectator-kicked. Report this please!'
                return
            if self.admin or self.rights.specpower:
                print 'WARNING 2. Safety check kept an admin from being spectator-kicked.'
                return
            if id == 1:
                seconds = floor(spectator_kick_time / 4)
                self.send_chat('Warning! If you do not leave spectator, you will be kicked in %s seconds!' % (seconds))
                self.spec_check = reactor.callLater(seconds, self.check_spec_time, 2)
            elif id == 2:
                self.kick('You have been kicked for remaining in spectator for too long.')
    return protocol, SpectatorControlConnection
