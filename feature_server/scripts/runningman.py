from pyspades.server import grenade_packet
from pyspades.collision import distance_3d_vector
from twisted.internet import reactor
from random import choice
from commands import add, admin, name

@admin
def relink(connection):
    for player in connection.protocol.players.values():
        player.drop_link()

@name('nolink')
@admin
def no_link(connection, value = None):
    if value is not None:
        connection = get_player(connection.protocol, value)
    if connection.link is not None:
        connection.link.link = None
    connection.link = None
    connection.linkable = not connection.linkable
    if connection.linkable:
        connection.protocol.send_chat("%s's collar hums back to life." %
            connection.name)
    else:
        connection.protocol.send_chat("%s is free as a bird." %
            connection.name)

@name('linkdistance')
@admin
def link_distance(connection, value = None):
    if value is not None:
        value = float(value)
        connection.protocol.link_distance = value
        connection.protocol.link_warning_distance = value * 0.8
        connection.protocol.send_chat('Link distance changed to %s' % value)
        return
    connection.send_chat('Link distance is currently %s' %
        connection.protocol.link_distance)

for func in (relink, no_link, link_distance):
    add(func)

def apply_script(protocol, connection, config):
    class RunningManConnection(connection):
        link = None
        linkable = True
        link_active = True
        last_warning = None
        
        def on_position_update(self):
            if self.link is not None and self.link_active and self.link.hp > 0:
                dist = distance_3d_vector(self.world_object.position,
                    self.link.world_object.position)
                if dist > self.protocol.link_distance:
                    grenade_packet.value = 0.0
                    grenade_packet.player_id = self.player_id
                    self.protocol.send_contained(grenade_packet)
                    self.kill()
                    grenade_packet.player_id = self.link.player_id
                    self.protocol.send_contained(grenade_packet)
                    self.link.kill()
                    message = ("You strayed too far from %s... don't go losing "
                        "your head over it.")
                    self.send_chat(message % self.link.name)
                    self.link.send_chat(message % self.name)
                elif dist > self.protocol.link_warning_distance:
                    if (self.last_warning is None or
                        reactor.seconds() - self.last_warning > 2.0):
                        message = 'WARNING! Get back to %s or you will both die!'
                        self.send_chat(message % self.link.name)
                        self.link.send_chat(message % self.name)
                        self.last_warning = reactor.seconds()
            connection.on_position_update(self)
        
        def get_new_link(self):
            available = [p for p in self.team.get_players() if
                (p is not self and p.link is None and self.link is not p)]
            if len(available) > 0:
                self.link = choice(available)
                self.link.link = self
                message = ("You've been linked to %s.  Stay close to your"
                    "partner or die!")
                self.send_chat(message % self.link.name)
                self.link.send_chat(message % self.name)
            elif self.link is not None and self.link.linkable == False:
                self.drop_link()
        
        def on_spawn(self, pos):
            if self.link is None:
                self.get_new_link()
            if self.link is not None and self.link.hp > 0:
                pos = self.link.world_object.position.get()
                self.set_location(pos)
            connection.on_spawn(self, pos)
        
        def on_team_join(self, team):
            if self.team is not team and self.link is not None:
                self.link.drop_link()
                self.link = None
        
        def disconnect(self):
            if self.link is not None:
                self.link.drop_link()
            connection.disconnect(self)
        
        def drop_link(self):
            if self.link.hp > 0:
                self.send_chat("You're free to roam around... for now.")
            self.link = None
    
    class RunningManProtocol(protocol):
        link_distance = 40.0
        link_warning_distance = link_distance * 0.8
    
    return RunningManProtocol, RunningManConnection