from pyspades.server import orientation_data, grenade_packet
from pyspades.common import coordinates, Vertex3
from pyspades.collision import distance_3d_vector
from pyspades.world import Grenade
from twisted.internet import reactor
import random
import commands

def airstrike(connection, value = None):
    return connection.start_airstrike(value)

commands.add(airstrike)

def apply_script(protocol, connection, config):
    class AirstrikeConnection(connection):
        airstrike = False
        def desync_grenade(self, x, y, z, orientation_x, fuse):
            """Gives the appearance of a grenade appearing from thin air"""
            if self.name is None:
                return
            grenade_packet.value = fuse
            grenade_packet.player_id = self.player_id
            grenade_packet.position = (x, y, z)
            grenade_packet.velocity = (orientation_x, 0.0, 0.5)
            self.protocol.send_contained(grenade_packet)
            position = Vertex3(x, y, z)
            velocity = Vertex3(orientation_x, 0.0, 0.5)
            airstrike = self.protocol.world.create_object(Grenade, fuse, 
                position, None, 
                velocity, self.grenade_exploded)
            airstrike.name = 'airstrike'
            
        # airstrike
        
        def start_airstrike(self, value = None):
            score_req = self.protocol.airstrike_min_score_req
            streak_req = self.protocol.airstrike_streak_req
            interval = self.protocol.airstrike_interval
            if value is None and (self.god or self.airstrike):
                return 'Airstrike support ready! Use with e.g. /airstrike A1'
            if self.kills < score_req:
                return ('You need a total score of %s (kills or intel) to '
                    'unlock airstrikes!' % score_req)
            elif not self.airstrike:
                kills_left = streak_req - (self.streak % streak_req)
                return ('Every %s consecutive kills (without dying) you '
                    'get an airstrike. %s kills to go!' %
                    (streak_req, kills_left))
            try:
                x, y = coordinates(value)
            except (ValueError):
                return ("Bad coordinates: should be like 'A4', 'G5'. Look "
                    "them up in the map.")
            last_airstrike = self.protocol.last_airstrike[self.team.id]
            if (last_airstrike and reactor.seconds() - last_airstrike < interval):
                remain = interval - (reactor.seconds() - last_airstrike)
                return ('%s seconds before your team can launch '
                    'another airstrike.' % int(remain))
            self.protocol.last_airstrike[self.team.id] = reactor.seconds()
            
            self.airstrike = False
            self.protocol.send_chat('Ally %s called in an airstrike on '
                'location %s' % (self.name, value.upper()), global_message = False,
                team = self.team)
            self.protocol.send_chat('[WARNING] Enemy air support heading to %s!' %
                value.upper(), global_message = False, team = self.team.other)
            reactor.callLater(2.5, self.do_airstrike, x, y)
        
        def do_airstrike(self, start_x, start_y):
            if self.name is None:
                return
            z = 1
            orientation_x = [1.0, -1.0][self.team.id]
            start_x = max(0, min(512, start_x + [-64, 64][self.team.id]))
            range_x = [61, -61][self.team.id]
            increment_x = [5, -5][self.team.id]
            for round in xrange(12):
                x = start_x + random.randrange(64)
                y = start_y + random.randrange(64)
                fuse = self.protocol.map.get_height(x + range_x, y) * 0.033
                for i in xrange(5):
                    x += increment_x
                    time = round * 0.9 + i * 0.14
                    reactor.callLater(time, self.desync_grenade, x, y, z,
                        orientation_x, fuse)
        
        def add_score(self, score):
            connection.add_score(self, score)
            score_req = self.protocol.airstrike_min_score_req
            streak_req = self.protocol.airstrike_streak_req
            score_met = (self.kills >= score_req)
            streak_met = (self.streak >= streak_req)
            give_strike = False
            if not score_met:
                return
            if self.kills - score < score_req:
                self.send_chat('You have unlocked airstrike support!')
                self.send_chat('Each %s-kill streak will clear you for one '
                               'airstrike.' % streak_req)
                if streak_met:
                    give_strike = True
            if not streak_met:
                return
            if (self.streak % streak_req == 0 or give_strike):
                self.send_chat('Airstrike support ready! Launch with e.g. '
                               '/airstrike B4')
                self.airstrike = True
                self.refill()
    
    class AirstrikeProtocol(protocol):
        last_airstrike = [None, None]
        airstrike_min_score_req = 15
        airstrike_streak_req = 6
        airstrike_interval = 12
    
    return AirstrikeProtocol, AirstrikeConnection