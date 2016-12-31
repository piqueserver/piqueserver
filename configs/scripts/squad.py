"""
BF-like squad system.

Maintainer: Triplefox
"""

from commands import add, rights, admin, name, get_player
import commands
import random

SQUAD_NAMES = set([
    'Alpha','Bravo','Charlie','Delta','Epsilon','Foxtrot','Gamma',
   'Golf','Hotel','India','Juliet','Kilo','Lima','Mike',
   'November','Oscar','Papa','Quebec','Romero','Sierra','Tango',
   'Uniform','Victor','Whiskey','X-ray','Yankee','Zulu'])

def follow(self, playerkey = None):
    if playerkey is None:
        squad_pref = None
        squad = self.squad
    else:
        squad_pref = get_player(self.protocol, playerkey)
        squad = squad_pref.squad
        if squad_pref.team is not self.team:
            return '%s is not on your team!' % (squad_pref.name)
        if squad_pref is self:
            return "You can't follow yourself!"
        if squad_pref.squad is None:
            return ('%s is not in a squad and cannot be followed.' %
                    squad_pref.name)

    return self.join_squad(squad, squad_pref)

def squad(self, squadkey = None):
    if self.protocol.squad_size <= 1:
        return 'Squads are disabled on this server.'

    # squadlist

    if squadkey is None:
        allsquads = self.get_squads(self.team)
        result = []
        for squadkey in allsquads.keys():
            result.append(self.print_squad(
            squadkey, allsquads[squadkey]))
        result.append(('To join squads: /squad <squad name>. ' +
                       '/squad none to spawn normally.'))
        self.send_lines(result)
        return

    if squadkey.lower() == 'none':
        squad = None
        squad_pref = None
    else:
        squad = squadkey
        squad_pref = None

    return self.join_squad(squad, squad_pref)

for func in (squad, follow):
    add(func)

def apply_script(protocol, connection, config):
    protocol.squad_respawn_time = config.get('squad_respawn_time',
        protocol.respawn_time)
    protocol.squad_size = config.get('squad_size', 0)
    protocol.auto_squad = config.get('auto_squad', True)

    class SquadConnection(connection):
        squad = None
        squad_pref = None

        def on_login(self, name):
            if self.protocol.auto_squad:
                self.join_squad(self.find_auto_squad(),None)
            return connection.on_login(self, name)

        def get_squad(self, team, squadkey):
            result = {'name' : squadkey, 'players' : []}
            if squadkey is None:
                for player in self.protocol.players.values():
                    if (player.team is team and
                        player.squad is None):
                        result['players'].append(player)
                        result['name'] = player.squad
            else:
                for player in self.protocol.players.values():
                    if (player.team is team and player.squad and
                        player.squad.lower() == squadkey.lower()):
                        result['players'].append(player)
                        result['name'] = player.squad
            return result

        def get_squads(self, team):
            squad_dict = {}
            for player in self.protocol.players.values():
                if player.team is team:
                    if squad_dict.has_key(player.squad):
                        squad_list = squad_dict[player.squad]
                    else:
                        squad_list = []
                        squad_dict[player.squad] = squad_list
                    squad_list.append(player)
            return squad_dict

        def print_squad(self, squadkey, squadlist):
            if squadkey is None:
                result = 'Unassigned: '
            else:
                result = 'Squad %s: ' % (squadkey)
            result+=', '.join([player.name for player in squadlist])
            return result

        def find_auto_squad(self):
            squad_dict = self.get_squads(self.team)
            available = set()
            unused = []
            for name in SQUAD_NAMES:
                if squad_dict.has_key(name):
                    if len(squad_dict[name]) < self.protocol.squad_size:
                        available.add(name)
                else:
                    unused.append(name)
            if len(available) > 0:
                return available.pop()
            else:
                return random.choice(unused)

        def join_squad(self, squad, squad_pref):

            if self.team is None or \
               self.team is self.protocol.spectator_team:
                return

            # same-squad check

            if squad is None or self.squad is None:
                newsquad = self.squad is not squad
            else:
                newsquad = self.squad.lower() != squad.lower()
            newpref = self.squad_pref is not squad_pref

            if not newsquad and not newpref:
                return 'Squad unchanged.'

            # unique squad, so check for squad size first

            existing = self.get_squad(self.team, squad)
            squad = existing['name'] # fixes the case

            if squad and (self.protocol.squad_size
                <= len(existing['players'])):
                return ('Squad %s is full. (limit %s)' %
                        (squad, self.protocol.squad_size))

            # assign to unique squad

            oldsquad = self.squad
            oldpref = self.squad_pref

            if newsquad and self.squad:
                self.leave_squad()

            self.squad = squad
            self.squad_pref = squad_pref

            if newsquad and squad:
                self.squad_broadcast('%s joined your squad.' %
                                           self.name)

            if squad is None:
                self.respawn_time = self.protocol.respawn_time
                self.squad_pref = None
                self.send_chat('You are no longer assigned to a squad.')
            else:
                self.respawn_time = self.protocol.squad_respawn_time
                if newpref and newsquad:
                    if squad_pref is None:
                        return ('You are now in squad %s.' % squad)
                    else:
                        return ('You are now in squad %s, following %s.' %
                                   (squad, squad_pref.name))
                elif newpref:
                    if squad_pref is None:
                        return ('You are no longer following %s.' %
                                oldpref.name)
                    else:
                        return ('You are now following %s.' %
                                   squad_pref.name)
                elif newsquad:
                    return 'You are now in squad %s.' % squad

        def leave_squad(self):
            if self.squad:
                self.squad_broadcast("%s left your squad." %
                                           self.name)
            self.squad = None
            self.squad_pref = None
            for player in self.protocol.players.values():
                if player.squad_pref is self:
                    player.squad_pref = None
            self.respawn_time = self.protocol.respawn_time

        def squad_broadcast(self, msg):
            if self.squad:
                squad = self.get_squad(self.team, self.squad)
                for player in squad['players']:
                    if player is not self:
                        player.send_chat(msg)

        def get_follow_location(self, follow):
            x, y, z = (follow.world_object.position.get())
            return x, y, z

        def on_team_changed(self, old_team):
            self.leave_squad()
            return connection.on_team_changed(self, old_team)

        def on_spawn(self, pos):
            if self.squad:
                all_members = ([n for n in self.get_squad(self.team,
                            self.squad)['players'] if
                            n is not self])
                live_members = [n for n in all_members if n.hp]
                membernames = [m.name for m in all_members]
                memberstr = ""
                for n in xrange(len(all_members)):
                    name = membernames[n]
                    if not all_members[n].hp:
                        name += " (DEAD)"
                    else:
                        name += " (%s hp)" % all_members[n].hp
                    if n==0:
                        memberstr+="%s" % name
                    elif n==len(membernames)-1:
                        memberstr+=" and %s" % name
                    else:
                        memberstr+=", %s" % name
                if len(all_members)>0:
                    self.send_chat('You are in squad %s with %s.' %
                                   (self.squad, memberstr))
                else:
                    self.send_chat('You are in squad %s, all alone.' %
                                   self.squad)
                if (self.squad_pref is not None and self.squad_pref.hp and
                    self.squad_pref.team is self.team):
                    self.set_location_safe(self.get_follow_location(
                        self.squad_pref))
                else:
                    if len(live_members)>0:
                        self.set_location_safe(self.get_follow_location(
                            random.choice(live_members)))
            return connection.on_spawn(self, pos)

        def on_kill(self, killer, type, grenade):
            if killer is None or killer is self:
                self.squad_broadcast('Squadmate %s suicided' % self.name)
            else:
                self.squad_broadcast('Squadmate %s was killed by %s' %
                             (self.name, killer.name))
            return connection.on_kill(self, killer, type, grenade)

        def on_chat(self, value, global_message):
            if self.squad is not None and not global_message:
                value = '%s : %s' % (self.squad, value)
            return connection.on_chat(self, value, global_message)

    return protocol, SquadConnection
