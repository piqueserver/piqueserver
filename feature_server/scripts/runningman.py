from pyspades.server import grenade_packet
from pyspades.collision import distance_3d_vector
from twisted.internet import reactor
from random import choice
from commands import add, admin, name, get_player

@admin
def relink(connection):
    connection.protocol.drop_all_links()
    connection.protocol.send_chat('All players unlinked.', irc = True)

@name('nolink')
@admin
def no_link(connection, value = None):
    if value is not None:
        connection = get_player(connection.protocol, value)
    connection.drop_link()
    connection.linkable = not connection.linkable
    if connection.linkable:
        connection.protocol.send_chat("%s's collar hums back to life." %
            connection.name, irc = True)
    else:
        connection.protocol.send_chat('%s is free as a bird.' %
            connection.name, irc = True)

@name('linkdistance')
@admin
def link_distance(connection, value):
    value = float(value)
    connection.protocol.link_distance = value
    connection.protocol.link_warning_distance = value * 0.65
    connection.protocol.send_chat('Link distance changed to %s' % value,
        irc = True)

for func in (relink, no_link, link_distance):
    add(func)

def apply_script(protocol, connection, config):
    class RunningManConnection(connection):
        link = None
        linkable = True
        last_warning = None
        link_deaths = None
        
        def on_position_update(self):
            if self.link is not None and self.link.hp > 0:
                dist = distance_3d_vector(self.world_object.position,
                    self.link.world_object.position)
                if dist > self.protocol.link_distance:
                    grenade_packet.value = 0.0
                    grenade_packet.player_id = self.player_id
                    grenade_packet.position = self.world_object.position.get()
                    grenade_packet.acceleration = self.world_object.orientation.get()
                    self.protocol.send_contained(grenade_packet)
                    self.kill()
                    grenade_packet.player_id = self.link.player_id
                    grenade_packet.position = (
                        self.link.world_object.position.get())
                    self.protocol.send_contained(grenade_packet)
                    self.link.kill()
                    message = ("You strayed too far from %s... don't go losing "
                        "your head over it.")
                    self.send_chat(message % self.link.name)
                    self.link.send_chat(message % self.name)
                    self.link_deaths += 1
                    self.link.link_deaths += 1
                elif dist > self.protocol.link_warning_distance:
                    if (self.last_warning is None or
                        reactor.seconds() - self.last_warning > 2.0):
                        message = 'WARNING! Get back to %s or you will both die!'
                        self.send_chat(message % self.link.name)
                        self.link.send_chat(message % self.name)
                        self.last_warning = reactor.seconds()
                        self.link.last_warning = reactor.seconds()
            connection.on_position_update(self)
        
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
            if len(available) == 0:
                return
            self.drop_link(force_message = True)
            self.link = choice(available)
            self.link.drop_link(force_message = True)
            self.link.link = self
            self.link_deaths = 0
            self.link.link_deaths = 0
            message = ("You've been linked to %s. Stay close to your "
                "partner or die!")
            self.send_chat(message % self.link.name)
            self.link.send_chat(message % self.name)
        
        def on_spawn(self, pos):
            if (self.link is None or
                self.link_deaths >= self.protocol.link_death_max):
                self.get_new_link()
            if self.link is not None and self.link.hp > 0:
                x, y, z = self.link.world_object.position.get()
                z -= 2
                self.set_location((x, y, z))
            connection.on_spawn(self, pos)
        
        def on_team_join(self, team):
            if self.team is not team:
                self.drop_link()
        
        def on_flag_capture(self):
            self.protocol.drop_all_links()
        
        def disconnect(self):
            connection.disconnect(self)
            self.drop_link()
        
        def drop_link(self, force_message = False):
            if self.link is None:
                return
            if self.link.hp > 0 or force_message:
                self.link.send_chat("You're free to roam around... for now.")
            self.link.link = None
            self.link = None
    
    class RunningManProtocol(protocol):
        link_distance = 40.0
        link_warning_distance = link_distance * 0.65
        link_death_max = 2
        
        def drop_all_links(self):
            for player in self.players.values():
                player.drop_link()
                player.send_chat("You're free to roam around... for now.")
    
    return RunningManProtocol, RunningManConnection