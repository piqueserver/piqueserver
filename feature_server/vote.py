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

def cancel_verify(connection, instigator):
    return (connection.admin or 
            connection is instigator or 
            connection.rights.cancel)

#TODO: make this a script like votekick.

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
        rotation = [n.name.lower() for n in rotation]
        final_rotation = random.sample(rotation, min(len(rotation),5))
        if self.extension_time>0:
            final_rotation.append("extend")
        self.picks = final_rotation
        self.votes = {}
        self.schedule = Schedule(protocol, [
            AlarmLater(self.timeout, seconds=self.vote_time),
            AlarmLater(self.update, seconds=30, loop=True,
                       traversal_required=False)], None,
                        "Votemap by %s" % connection.name)

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
        if connection is None:
            message = 'Cancelled'
        elif not cancel_verify(connection, self.instigator):
            return 'You did not start the vote.'
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
# consider reworking to generator style
