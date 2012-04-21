"""
Links any two teammates so that they explode if they stray away from each other.
An incredibly unnerving method of encouraging teamplay.

Enable by doing /runningman or by setting ENABLED_AT_START = True
Linking is automatic at spawn and tries to find new partners every two deaths.
Use /unlink [player] to toggle yourself or someone from being linked.

May not work well with squads.

Maintainer: hompy
"""

from random import choice
from itertools import ifilter
from twisted.internet.reactor import seconds
from pyspades.world import Grenade
from pyspades.server import grenade_packet
from pyspades.collision import distance_3d_vector
from pyspades.constants import *
from pyspades.common import Vertex3
from commands import add, admin, get_player, name

ENABLED_AT_START = False

LINK_DISTANCE = 40.0
LINK_WARNING_DISTANCE = LINK_DISTANCE * 0.65
MAX_LINK_DEATHS = 2

S_ENABLED = 'Running Man mode ENABLED'
S_DISABLED = 'Running Man mode DISABLED'
S_NOT_ENABLED = 'Running Man mode is not enabled'
S_LINK_BREAK = "You strayed too far from {player}... don't go losing your " \
    "head over it"
S_LINK_WARNING = 'WARNING! Get back to {player} or you will both die!'
S_LINKED = "You've been linked to {player}. Stay close to your partner or die!"
S_FREE = "You're free to roam around... for now"
S_LINKABLE = "{player}'s collar hums back to life"
S_LINKABLE_SELF = "Your collar hums back to life"
S_UNLINKABLE = '{player} is free as a bird'
S_UNLINKABLE_SELF = "You're free as a bird"
S_UNLINK_ALL = 'All players unlinked!'
S_FLAG_CAPTURED = 'The intel capture has unlinked everyone in the {team} team!'

@admin
@name('runningman')
def running_man(connection):
    protocol = connection.protocol
    protocol.running_man = not protocol.running_man
    if not protocol.running_man:
        protocol.drop_all_links()
    message = S_ENABLED if protocol.running_man else S_DISABLED
    protocol.send_chat(message, irc = True)

@admin
def relink(connection):
    if not connection.protocol.running_man:
        return S_NOT_ENABLED
    connection.protocol.drop_all_links()
    connection.protocol.send_chat(S_UNLINK_ALL, irc = True)

@admin
def unlink(connection, player = None):
    protocol = connection.protocol
    if not protocol.running_man:
        return S_NOT_ENABLED
    
    if player is not None:
        player = get_player(protocol, player)
    elif connection in protocol.players:
        player = connection
    else:
        raise ValueError()
    
    player.drop_link()
    player.linkable = not player.linkable
    player.send_chat(S_LINKABLE_SELF if player.linkable else S_UNLINKABLE_SELF)
    message = S_LINKABLE if player.linkable else S_UNLINKABLE
    message.format(player = player.name)
    if connection is not player:
        return message
    
for func in (running_man, relink, unlink):
    add(func)

def apply_script(protocol, connection, config):
    class RunningManConnection(connection):
        link = None
        linkable = True
        last_warning = None
        link_deaths = None
        
        def on_position_update(self):
            if self.protocol.running_man:
                if self.link is not None and self.link.hp > 0:
                    dist = distance_3d_vector(self.world_object.position,
                        self.link.world_object.position)
                    if dist > LINK_DISTANCE:
                        self.grenade_suicide()
                        self.link_deaths += 1
                        self.link.grenade_suicide()
                        self.link.link_deaths += 1
                        
                        message = S_LINK_BREAK.format(player = self.link.name)
                        self.send_chat(message)
                        message = S_LINK_BREAK.format(player = self.name)
                        self.link.send_chat(message)
                    elif (dist > LINK_WARNING_DISTANCE and 
                        (self.last_warning is None or 
                        seconds() - self.last_warning > 2.0)):
                        
                        self.last_warning = seconds()
                        self.link.last_warning = seconds()
                        
                        message = S_LINK_WARNING.format(player = self.link.name)
                        self.send_chat(message)
                        message = S_LINK_WARNING.format(player = self.name)
                        self.link.send_chat(message)
            connection.on_position_update(self)
        
        def on_spawn(self, pos):
            if self.protocol.running_man:
                if (self.link is None or
                    self.link_deaths >= MAX_LINK_DEATHS):
                    self.get_new_link()
                if self.link is not None and self.link.hp > 0:
                    self.set_location_safe(self.link.world_object.position.get())
            connection.on_spawn(self, pos)
        
        def on_team_changed(self, old_team):
            if self.protocol.running_man:
                self.drop_link()
            return connection.on_team_changed(self, old_team)
        
        def on_flag_capture(self):
            if self.protocol.running_man:
                for player in self.team.get_players():
                    player.drop_link(no_message = True)
                message = S_FLAG_CAPTURED.format(team = self.team.name)
                self.protocol.send_chat(message, global_message = None)
            connection.on_flag_capture(self)
        
        def on_reset(self):
            if self.protocol.running_man:
                self.drop_link()
            connection.on_reset(self)
        
        def can_be_linked_to(self, player):
            if self is player or self.link is player:
                return False
            if player.link is not None and player.link_deaths < MAX_LINK_DEATHS:
                return False
            return True
        
        def get_new_link(self):
            available = list(ifilter(self.can_be_linked_to,
                self.team.get_players()))
            if not available:
                return
            self.drop_link(force_message = True)
            self.link = choice(available)
            self.link_deaths = 0
            self.link.drop_link(force_message = True)
            self.link.link = self
            self.link.link_deaths = 0
            
            message = S_LINKED.format(player = self.link.name)
            self.send_chat(message)
            message = S_LINKED.format(player = self.name)
            self.link.send_chat(message)
        
        def drop_link(self, force_message = False, no_message = False):
            if self.link is None:
                return
            if (self.link.hp > 0 or force_message) and not no_message:
                self.link.send_chat(S_FREE)
            self.link.link = None
            self.link = None
        
        def grenade_suicide(self):
            protocol = self.protocol
            position = self.world_object.position
            protocol.world.create_object(Grenade, 0.0, position, None,
                Vertex3(), self.grenade_exploded)
            grenade_packet.value = 0.0
            grenade_packet.player_id = self.player_id
            grenade_packet.position = position.get()
            grenade_packet.velocity = (0.0, 0.0, 0.0)
            protocol.send_contained(grenade_packet)
            self.kill(type = GRENADE_KILL)
    
    class RunningManProtocol(protocol):
        running_man = ENABLED_AT_START
        
        def drop_all_links(self):
            for player in self.players.values():
                player.drop_link(no_message = True)
    
    return RunningManProtocol, RunningManConnection