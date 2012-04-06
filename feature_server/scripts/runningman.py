"""
Links two teammates so that they explode if they stray away from each other.
An incredibly unnerving method of encouraging teamplay.

Enable by doing /runningman or by setting ENABLED_AT_START = True

Maintainer: hompy
"""

from random import choice
from twisted.internet.reactor import seconds
from pyspades.world import Grenade
from pyspades.server import grenade_packet
from pyspades.collision import distance_3d_vector
from commands import add, admin, name, get_player

ENABLED_AT_START = False

S_ENABLED = 'Running man mode ENABLED'
S_DISABLED = 'Running man mode DISABLED'
S_LINK_BREAK = "You strayed too far from {player}... don't go losing your head over it"
S_LINK_WARNING = 'WARNING! Get back to {player} or you will both die!'
S_LINKED = "You've been linked to {player}. Stay close to your partner or die!"
S_FREE = "You're free to roam around... for now"
S_LINKABLE = "{player}'s collar hums back to life"
S_UNLINKABLE = '{player} is free as a bird'
S_UNLINK_ALL = 'All players unlinked'

@admin
@name('runningman')
def running_man(connection):
    protocol = connection.protocol
    protocol.running_man = not protocol.running_man
    if protocol.running_man:
        protocol.send_chat(S_ENABLED, irc = True)
    else:
        protocol.send_chat(S_DISABLED, irc = True)
        protocol.drop_all_links()

@admin
def relink(connection):
    connection.protocol.drop_all_links()
    connection.protocol.send_chat(S_UNLINK_ALL, irc = True)

@name('nolink')
@admin
def no_link(connection, player = None):
    protocol = connection.protocol
    if player is not None:
        player = get_player(protocol, player)
    elif connection in protocol.players:
        player = connection
    else:
        raise ValueError()
    
    player.drop_link()
    player.linkable = not player.linkable
    if player.linkable:
        message = S_LINKABLE.format(player = player.name)
    else:
        message = S_UNLINKABLE.format(player = player.name)
    protocol.send_chat(message, irc = True)

for func in (running_man, relink, no_link):
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
                    if dist > self.protocol.link_distance:
                        self.grenade_suicide()
                        self.link_deaths += 1
                        self.grenade_suicide()
                        self.link.link_deaths += 1
                        
                        message = S_LINK_BREAK.format(player = self.link.name)
                        self.send_chat(message)
                        message = S_LINK_BREAK.format(player = self.name)
                        self.link.send_chat(message)
                    elif dist > self.protocol.link_warning_distance:
                        if (self.last_warning is None or 
                            seconds() - self.last_warning > 2.0):
                            self.last_warning = seconds()
                            self.link.last_warning = seconds()
                            
                            message = S_LINK_WARNING.format(
                                player = self.link.name)
                            self.send_chat(message)
                            message = S_LINK_WARNING.format(player = self.name)
                            self.link.send_chat(message)
            connection.on_position_update(self)
        
        def on_spawn(self, pos):
            if self.protocol.running_man:
                if (self.link is None or
                    self.link_deaths >= self.protocol.link_death_max):
                    self.get_new_link()
                if self.link is not None and self.link.hp > 0:
                    self.set_location_safe(self.link.world_object.position.get())
            connection.on_spawn(self, pos)
        
        def on_team_join(self, team):
            if self.protocol.running_man and self.team is not team:
                self.drop_link()
            return connection.on_team_join(self, team)
        
        def on_flag_capture(self):
            if self.protocol.running_man:
                self.protocol.drop_all_links()
            connection.on_flag_capture(self)
        
        def on_reset(self):
            if self.protocol.running_man:
                self.drop_link()
            connection.on_reset(self)
        
        def can_be_linked_to(self, player):
            if self is player or self.link is player:
                return False
            if (player.link is not None and
                player.link_deaths < self.protocol.link_death_max):
                return False
            return True
        
        def get_new_link(self):
            available = [player for player in self.team.get_players() if 
                self.can_be_linked_to(player)]
            if not available:
                return
            self.drop_link(force_message = True)
            self.link = choice(available)
            self.link_deaths = 0
            self.link.drop_link(force_message = True)
            self.link.link = self
            self.link.link_deaths = 0
            
            message = S_LINKED.format(player = self.link.name)
            self.send_chat(message % self.link.name)
            message = S_LINKED.format(player = self.name)
            self.link.send_chat(message % self.name)
        
        def drop_link(self, force_message = False):
            if self.link is None:
                return
            if self.link.hp > 0 or force_message:
                self.link.send_chat(S_FREE)
            self.link.link = None
            self.link = None
        
        def grenade_suicide(self):
            protocol = self.protocol
            position = self.world_object.position
            protocol.world.create_object(Grenade, 0.0, position, None,
                Vertex3(), protocol.grenade_exploded)
            grenade_packet.value = 0.0
            grenade_packet.player_id = self.player_id
            grenade_packet.position = position.get()
            grenade_packet.velocity = (0.0, 0.0, 0.0)
            protocol.send_contained(grenade_packet)
            self.kill()
    
    class RunningManProtocol(protocol):
        running_man = ENABLED_AT_START
        link_distance = 40.0
        link_warning_distance = link_distance * 0.65
        link_death_max = 2
        
        def drop_all_links(self):
            for player in self.players.values():
                player.drop_link()
                player.send_chat(S_FREE)
    
    return RunningManProtocol, RunningManConnection