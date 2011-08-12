from pyspades.server import player_data, chat_message
from pyspades.server import create_player, position_data, kill_action
from commands import add, rights, admin, name, get_player
import commands
import random

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
        for squadkey in allsquads.keys():
            self.send_chat(self.print_squad(
            squadkey, allsquads[squadkey]))
        return ('To join squads: /squad <squad name>. /squad none to spawn normally.')

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
    
    class SquadConnection(connection):
        squad = None
        squad_pref = None
        
        def get_squad(self, team, squadkey):
            result = []
            for player in self.protocol.players.values():
                if player.team is team and player.squad == squadkey:
                    result.append(player)
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
            if squadkey == None:
                result = 'Unassigned: '
            else:
                result = 'Squad %s: ' % (squadkey)
            result+=', '.join([player.name for player in squadlist])
            return result

        def join_squad(self, squad, squad_pref):
            
            # same-squad check
            
            if self.squad == squad and self.squad_pref is squad_pref:
                return 'Squad unchanged.'

            # unique squad, so check for squad size first
            
            if squad != None and (self.protocol.squad_size
                <= len(self.get_squad(self.team, squad))):
                return ('Squad %s is full. (limit %s)' %
                        self.protocol.squad_size)
            
            # assign to unique squad

            newsquad = self.squad != squad
            newpref = self.squad_pref != squad_pref

            oldsquad = self.squad
            oldpref = self.squad_pref
            
            if newsquad and self.squad is not None:
                self.leave_squad()

            self.squad = squad
            self.squad_pref = squad_pref
            
            if newsquad and squad is not None:
                self.squad_broadcast('%s joined your squad.' %
                                           self.name)
            
            if squad == None:
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
            if self.squad is not None:
                self.squad_broadcast("%s left your squad." %
                                           self.name)
            self.squad = None
            self.squad_pref = None
            for player in self.protocol.players.values():
                if player.squad_pref is self:
                    player.squad_pref = None
            self.respawn_time = self.protocol.respawn_time

        def squad_broadcast(self, msg):
            if self.squad is not None:
                squad = self.get_squad(self.team, self.squad)
                for player in squad:
                    if player is not self:
                        player.send_chat(msg)
                    
        def get_follow_location(self, follow):
            x, y, z = (follow.world_object.position.get())
            z -= 2
            return x, y, z

        def on_team_leave(self):
            self.leave_squad()
            return connection.on_team_leave(self)

        def on_spawn(self, pos):
            if self.squad is not None:
                if (self.squad_pref is not None and self.squad_pref.hp and
                    self.squad_pref.team is self.team):
                    self.set_location(self.get_follow_location(
                        self.squad_pref))
                else:
                    members = ([n for n in self.get_squad(self.team,
                                self.squad) if n.hp and n is not self])
                    if len(members)>0:
                        self.set_location(self.get_follow_location(
                            random.choice(members)))
            return connection.on_spawn(self, pos)

        def on_kill(self, killer):
            if killer is None or killer is self:
                self.squad_broadcast('Squadmate %s suicided' % self.name)
            else:
                self.squad_broadcast('Squadmate %s was killed by %s' %
                             (self.name, killer.name))
            return connection.on_kill(self, killer)
       
    
    return protocol, SquadConnection
