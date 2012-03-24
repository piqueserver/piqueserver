# Copyright (c) James Hofmann 2012.

# This file is part of pyspades.

# pyspades is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

# pyspades is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with pyspades.  If not, see <http://www.gnu.org/licenses/>.

from twisted.internet import reactor
from twisted.internet.task import LoopingCall
from pyspades.common import prettify_timespan
from map import check_rotation
import random
from schedule import Schedule, AlarmLater, AlarmBeforeEnd

class VoteKick(object):
    public_votes = True
    ban_duration = 0.0
    instigator = None
    target = None
    protocol = None
    reason = None
    kicked = False
    
    def __init__(self, connection, player, reason = None):
        if reason is None:
            reason = 'NO REASON GIVEN'
        self.instigator = connection
        self.target = player
        self.protocol = connection.protocol
        self.vote_percentage = self.protocol.votekick_percentage
        self.vote_interval = self.protocol.votekick_interval
        self.schedule = Schedule(self.protocol, [
            AlarmLater(self.timeout, minutes=self.protocol.votekick_time),
            AlarmLater(self.update, seconds=30,
                       loop=True, traversal_required=False)])
        self.ban_duration = self.protocol.votekick_ban_duration
        self.public_votes = self.protocol.votekick_public_votes
        self.reason = reason
        self.kicked = False
        self.votes = {self.instigator:True}
        
    def votes_left(self):
        return int(((len(self.protocol.players) - 1) / 100.0
            ) * self.vote_percentage) - len(self.votes)
            
    def verify(self):
        target = self.target
        instigator = self.instigator
        if self.votes_left() <= 0:
            return 'Not enough players on server.'
        elif target is instigator:
            return "You can't votekick yourself."
        elif target.admin:
            return 'Cannot votekick an administrator.'
        elif (target.rights and 'cancel' in target.rights):
            return 'Target has vote cancellation rights.'
        last = instigator.last_votekick
        if (last is not None and
        reactor.seconds() - last < self.vote_interval):
            return "You can't start a votekick now."
        return True
        
    def start(self):
        instigator = self.instigator
        target = self.target
        reason = self.reason
        protocol = self.protocol
        protocol.irc_say(
            '* %s initiated a votekick against player %s.%s' % (instigator.name,
            target.name, ' Reason: %s' % reason if reason else ''))
        protocol.send_chat(
            '%s initiated a VOTEKICK against player %s. Say /y to '
            'agree.' % (instigator.name, target.name), sender = instigator)
        protocol.send_chat('Reason: %s' % reason, sender = instigator)
        instigator.send_chat('You initiated a VOTEKICK against %s. '
            'Say /cancel to stop it at any time.' % target.name)
        instigator.send_chat('Reason: %s' % reason)
        self.protocol.schedule.queue(self.schedule)
        self.protocol.votekick = self
        
    def vote(self, connection):
        if connection is self.target:
            return "The votekick victim can't vote."
        if self.votes is None or connection in self.votes:
            pass
        else:
            self.votes[connection] = True
            if self.public_votes:
                self.protocol.send_chat('%s voted YES.' % connection.name)
        if self.votes_left() <= 0:
            self.on_majority()
            
    def cancel(self, connection = None):
        if connection is None:
            message = 'Cancelled'
        elif (connection and (not connection.admin and 
            connection is not self.instigator and
            (not connection.rights or 'cancel' not in connection.rights))):
            return 'You did not start the votekick.'
        else:
            message = 'Cancelled by %s' % connection.name
        self.show_result(message)
        self.finish()
        
    def update(self):
        reason = self.reason if self.reason else 'none'
        self.protocol.send_chat(
            '%s is votekicking %s for reason: %s. Say /y to vote '
            '(%s needed)' % (self.instigator.name,
            self.target.name, reason, self.votes_left()))
            
    def on_disconnect(self, connection):
        if self.kicked:
            return
        if self.instigator is connection:
            self.cancel(self.instigator)
        elif self.target is connection:
            self.show_result("%s left during votekick" % self.target.name)
            if self.protocol.votekick_ban_duration:
                self.do_kick()
        self.finish()
        
    def on_player_banned(self, connection):
        if not self.kicked:
            self.cancel(connection)
            
    def timeout(self):
        self.show_result("Votekick timed out")
        self.finish()
        
    def on_majority(self):
        self.show_result("Player kicked")
        self.kicked = True
        self.do_kick()
        self.finish()
        
    def show_result(self, result):
        self.protocol.send_chat('Votekick for %s has ended. %s.' % (
            self.target.name, result), irc = True)
        if not self.instigator.admin: # set the cooldown
            self.instigator.last_votekick = reactor.seconds()
            
    def do_kick(self):
        print "%s votekicked" % self.target.name
        if self.protocol.votekick_ban_duration:
            self.target.ban(self.reason, self.ban_duration)
        else:
            self.target.kick(silent = True)
            
    def finish(self):
        self.schedule.destroy()
        self.protocol.votekick = None

class VoteMap(object):
    extension_time = 0.0
    public_votes = True
    instigator = None
    protocol = None
    
    def __init__(self, connection, protocol, rotation):
        self.instigator = connection
        self.rotation = rotation
        self.protocol = protocol
        self.vote_percentage = self.protocol.votemap_percentage
        self.vote_time = self.protocol.votemap_time
        self.vote_interval = self.protocol.votemap_interval
        self.public_votes = self.protocol.votemap_public_votes
        self.extension_time = self.protocol.votemap_extension_time
        rotation = [n.text.lower() for n in rotation]
        final_rotation = random.sample(rotation, min(len(rotation),5))
        if self.extension_time>0:
            final_rotation.append("extend")
        self.picks = final_rotation
        self.votes = {}
        self.schedule = Schedule(protocol, [
            AlarmLater(self.timeout, seconds=self.vote_time),
            AlarmLater(self.update, seconds=30, loop=True,
                       traversal_required=False)])

    def votes_left(self):
        thresh = int((len(self.protocol.players)) *
                     self.vote_percentage / 100.0)
        counts = {}
        for v in self.votes.values():
            if counts.has_key(v):
                counts[v]['count']+=1
            else:
                counts[v] = {'name':v, 'count':1}
        cvlist = list(counts.values())
        if len(cvlist)<=0:
            return {'name':self.picks[0], 'count':0}
        mv = cvlist[0]
        for n in counts.keys():
            if counts[n]['count']>mv['count']:
                mv = n
        mv['count'] = thresh - mv['count']
        return mv
        
    def verify(self):
        instigator = self.instigator
        if instigator is None:
            return True
        last = instigator.last_votemap
        if (last is not None and
        reactor.seconds() - last < self.vote_interval):
            return "You can't start a vote now."
        return True
        
    def start(self):
        instigator = self.instigator
        protocol = self.protocol
        if instigator is None:
            protocol.send_chat(
            'Time to vote!', irc=True)
        else:
            protocol.send_chat(
            '* %s initiated a map vote.' % instigator.name, irc=True)
        self.protocol.schedule.queue(self.schedule)
        self.protocol.votemap = self
        self.update()
        
    def vote(self, connection, mapname):
        mapname = mapname.lower()
        if not mapname in self.picks:
            connection.send_chat("Map %s is not available." % mapname)
            return
        self.votes[connection] = mapname
        if self.public_votes:
            self.protocol.send_chat('%s voted for %s.' % (connection.name,
                                                          mapname))
        if self.votes_left()['count'] <= 0:
            self.on_majority()
            
    def cancel(self, connection = None):
        if (connection and (not connection.admin and 
            connection is not self.instigator and
            (not connection.rights or 'cancel' not in connection.rights))):
            return 'You did not start the vote.'
        if connection is None:
            message = 'Cancelled'
        else:
            message = 'Cancelled by %s' % connection.name
        self.protocol.send_chat(message)
        self.set_cooldown()
        self.finish()
        
    def update(self):
        self.protocol.send_chat(
            'Choose next map. Say /vote <name> to cast vote.')
        names = ' '.join(self.picks)
        self.protocol.send_chat('Maps: %s' % names)
        self.protocol.send_chat('To extend current map: /vote extend')
        
    def timeout(self):
        self.show_result()
        self.finish()
        
    def on_majority(self):
        self.show_result()
        self.finish()
        
    def show_result(self):
        result = self.votes_left()['name']
        if result == "extend":
            tl = self.protocol.set_time_limit(self.extension_time, True)
            span = prettify_timespan(tl * 60.0)
            self.protocol.send_chat('Mapvote ended. Current map will continue '
                'for %s.' % span, irc = True)
            if self.protocol.votemap_autoschedule > 0:
                vms = Schedule(self.protocol, [
                AlarmBeforeEnd(self.protocol.start_votemap,
                              seconds=self.protocol.votemap_autoschedule)])
                self.protocol.schedule.queue(vms)
            
        else:
            self.protocol.send_chat('Mapvote ended. Next map will be: %s.' % 
                result, irc = True)
            self.protocol.planned_map = check_rotation([result])[0]
        self.set_cooldown()
        
    def set_cooldown(self):
        if self.instigator is not None and not self.instigator.admin:
            self.instigator.last_votemap = reactor.seconds()
            
    def finish(self):
        self.schedule.destroy()
        self.protocol.votemap = None

# 2nd pass: add map suggest
