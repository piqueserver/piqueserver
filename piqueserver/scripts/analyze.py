"""
Shows a detailed analysis of a players shots

Commands
^^^^^^^^

* ``/analyze or /an <target>`` to show a detailed analysis of a players shots if they hit someone.
  Shows hit player, distance, dT in milliseconds (Delta Time- Time since previous shot that hit someone.
  Useful for detecting multiple bullet or rapid hacks), weapon, which body part it hit, and a basic counter that displays the number of hits of that type.

* ``/analyze or /an`` to disable it

.. codeauthor:: a_girl
 """

import time
from pyspades.collision import distance_3d_vector
from pyspades.constants import (HEADSHOT_KILL)
from piqueserver.commands import command, get_player


@command('analyze', 'an')
def analyze_shot(connection, player=None):
    protocol = connection.protocol
    if not protocol.analyzers:
        protocol.analyzers = {}
    if player is None:
        if connection.name in protocol.analyzers:
            del protocol.analyzers[connection.name]
            return 'You are no longer analyzing anyone.'

        return 'Please enter a target player to analyze.'

    player = get_player(protocol, player)
    if player not in protocol.players:
        raise ValueError("Target player is required")

    if connection.name in protocol.analyzers:
        if player.name == protocol.analyzers[connection.name]:
            del protocol.analyzers[connection.name]
            return 'You are no longer analyzing anyone.'

        protocol.analyzers[connection.name] = player.name
        connection.hs, connection.bs, connection.ls = 0, 0, 0
        return (
            'You are no longer analyzing {}. You are now analyzing {}.'.format(
                protocol.analyzers[connection.name], player.name))

    protocol.analyzers[connection.name] = player.name
    connection.hs, connection.bs, connection.ls = 0, 0, 0
    return 'You are now analyzing {}'.format(player.name)

body_damage_values = [49, 29, 27]
limb_damage_values = [33, 18, 16]

def apply_script(protocol, connection, config):
    class analyze_shotsConnection(connection):
        dist = ""
        weap = ""
        hs, bs, ls = 0, 0, 0
        prev_time = None
        body_part = ""

        def on_hit(self, hit_amount, hit_player, type, grenade):
            if self.name in list(self.protocol.analyzers.values()):
                if type == HEADSHOT_KILL or hit_amount in body_damage_values or hit_amount in limb_damage_values:
                    if not grenade:
                        dist = int(distance_3d_vector(
                            self.world_object.position, hit_player.world_object.position))
                        weap = self.weapon_object.name
                        self.pres_time = time.monotonic()
                        if self.prev_time is None:
                            dt = None
                        else:
                            dt = (self.pres_time - self.prev_time) * 1000
                        self.prev_time = time.monotonic()
                        if type == HEADSHOT_KILL:
                            body_part = "HEADSHOT"
                        elif hit_amount in body_damage_values:
                            body_part = "Body"
                        elif hit_amount in limb_damage_values:
                            body_part = "Limb"
                        for name in list(self.protocol.analyzers.keys()):
                            if self.protocol.analyzers[name] == self.name:
                                analyzer = get_player(self.protocol, name)
                                if analyzer not in self.protocol.players.values():
                                    raise ValueError()
                                else:
                                    if body_part == "HEADSHOT":
                                        analyzer.hs += 1
                                        counter = analyzer.hs
                                    elif body_part == "Body":
                                        analyzer.bs += 1
                                        counter = analyzer.bs
                                    elif body_part == "Limb":
                                        analyzer.ls += 1
                                        counter = analyzer.ls
                                    if dt is not None:
                                        analyzer.send_chat('%s shot %s dist: %d blocks dT: %.0f ms %s %s(%d)' % (
                                            self.name, hit_player.name, dist, dt, weap, body_part, counter))
                                    else:
                                        analyzer.send_chat('%s shot %s dist: %d blocks dT: NA %s %s(%d)' % (
                                            self.name, hit_player.name, dist, weap, body_part, counter))
            return connection.on_hit(self, hit_amount, hit_player, type, grenade)

        def on_weapon_set(self, value):
            if self.name in list(self.protocol.analyzers.values()):
                for name in self.protocol.analyzers:
                    if self.protocol.analyzers[name] == self.name:
                        analyzer = get_player(self.protocol, name)
                        analyzer.hs, analyzer.bs, analyzer.ls = 0, 0, 0
            return connection.on_weapon_set(self, value)

        def on_disconnect(self):
            if self.name in list(self.protocol.analyzers.values()):
                for name in list(self.protocol.analyzers.keys()):
                    if self.protocol.analyzers[name] == self.name:
                        del self.protocol.analyzers[name]
                        analyzer = get_player(self.protocol, name)
                        if name != self.name:
                            analyzer.send_chat(
                                'You are no longer analyzing %s.  Player disconnected.' % (self.name))
            if self.name in self.protocol.analyzers:
                del self.protocol.analyzers[self.name]
            return connection.on_disconnect(self)

    class analyze_protocol(protocol):
        analyzers = {}

        def on_map_change(self, map):
            self.analyzers = {}
            protocol.on_map_change(self, map)
    return analyze_protocol, analyze_shotsConnection
