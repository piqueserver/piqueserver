# maintained by triplefox

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
import commands

def cancel_verify(connection, instigator):
    return (connection.admin or 
            connection is instigator or 
            connection.rights.cancel)

def votekick(connection, value, *arg):
    reason = commands.join_arguments(arg)
    if connection not in connection.protocol.players:
        raise KeyError()
    player = None
    try:
        player = commands.get_player(connection.protocol, '#' + value)
    except commands.InvalidPlayer:
        player = commands.get_player(connection.protocol, value)
    return connection.start_votekick(player, reason)

@commands.name('y')
def vote_yes(connection):
    if connection not in connection.protocol.players:
        raise KeyError()
    if connection.protocol.vk_target is not None:
        return connection.votekick_vote()
    else:
        return 'No votekick in progress.'        

commands.add(votekick)
commands.add(vote_yes)

def apply_script(protocol, connection, config):
    class VotekickProtocol(protocol):

        vk_instigator = None
        vk_target = None
        vk_reason = None
        vk_schedule = None
        
        votekick_time = 120 # 2 minutes
        votekick_interval = 3 * 60 # 3 minutes
        votekick_percentage = 25.0
        
        votekick_ban_duration = config.get('votekick_ban_duration', 15)
        votekick_percentage = config.get('votekick_percentage', 25)
        votekick_public_votes = config.get('votekick_public_votes', True)
    
        def votekick_votes_available(self):
            return int(((len(self.players) - 1) / 100.0) *
                       self.votekick_percentage)
        
        def votekick_votes(self):
            count = 0
            for player in self.connections.values():
                if player.vk_vote_status is not None:
                    count += 1
            return count
            
        def votekick_votes_left(self):
            return self.votekick_votes_available() - self.votekick_votes()
        
        def on_map_change(self, map):
            self.votekick_cleanup()
            protocol.on_map_change(self, map)

        def on_ban(self, banee, reason, duration):
            if banee is self.vk_target:
                self.votekick_show_result("Banned by admin")
                self.votekick_cleanup()
            protocol.on_ban(self, connection, reason, duration)

        def votekick_timeout(self):
            self.votekick_show_result("Votekick timed out")
            self.votekick_cleanup()

        def votekick_cleanup(self):
            self.on_votekick_end()
            if self.vk_schedule is not None:
                self.vk_schedule.destroy()
            self.vk_instigator = None
            self.vk_target = None
        
        def votekick_majority(self):
            self.votekick_show_result("Player kicked")
            text = "%s votekicked" % self.vk_target.name
            print text
            if self.votekick_ban_duration:
                self.vk_target.ban(self.vk_reason,
                                   self.votekick_ban_duration)
            else:
                self.vk_target.kick(silent = True)
            self.votekick_cleanup()

        def votekick_can_continue(self):
            if self.votekick_votes_available() <= 0:
                self.votekick_show_result(
                    "Not enough players to continue vote.")
                self.votekick_cleanup()
                return False
            else:
                return True

        def votekick_update(self):
            if not self.votekick_can_continue():
                return
            if self.vk_reason is None:
                reason = 'none'
            else:
                reason = self.vk_reason
            self.send_chat(
                '%s is votekicking %s for reason: %s. Say /y to vote '
                '(%s needed)' % (self.vk_instigator.name,
                self.vk_target.name, reason, self.votekick_votes_left()))

        def votekick_show_result(self, result):
            self.send_chat('Votekick for %s has ended. %s.' % (
                self.vk_target.name, result), irc = True)
            if not self.vk_instigator.admin: # set the cooldown
                self.vk_instigator.last_votekick = reactor.seconds()
                
        def cancel_vote(self, connection):
            if self.vk_target is None:
                return connection.cancel_vote()
            if connection is None: # IRC
                message = 'Cancelled'
            elif not cancel_verify(connection, self.vk_instigator):
                return 'You did not start the votekick.'
            else: # in-game
                message = 'Cancelled by %s' % connection.name
            self.votekick_show_result(message)
            self.votekick_cleanup()

        def on_votekick_start(self):
            pass
        
        def on_votekick_end(self):
            pass
    
    class VotekickConnection(connection):

        vk_vote_status = None
        last_votekick = None

        def votekick_vote(self):
            if self is self.protocol.vk_target:
                return "The votekick victim can't vote."
            elif not self.protocol.votekick_can_continue():
                return
            else:
                if (self.protocol.votekick_public_votes and
                    self.vk_vote_status is None):
                    self.protocol.send_chat('%s voted YES.' % self.name)
                self.vk_vote_status = True
            if self.protocol.votekick_votes_left() <= 0:
                self.protocol.votekick_majority()
            
        def on_disconnect(self):
            if self.protocol.vk_target is self:
                self.protocol.votekick_show_result(
                    "%s left during votekick" % self.name)
                vk_target = self.protocol.vk_target
                self.protocol.vk_target = None # mute on_ban message
                self.ban(self.protocol.vk_reason,
                         self.protocol.votekick_ban_duration)
                self.protocol.vk_target = vk_target
                self.protocol.votekick_cleanup()
            elif self.protocol.vk_instigator is self:
                self.protocol.votekick_show_result(
                    "Instigator %s left during votekick" % self.name)
                self.protocol.votekick_cleanup()
            connection.on_disconnect(self)

        def kick(self, reason = None, silent = False):
            if self.protocol.vk_target is self:
                self.protocol.votekick_show_result("Kicked by admin")
                self.protocol.votekick_cleanup()
            if self.protocol.vk_instigator is self:
                self.protocol.votekick_show_result("Instigator kicked by admin")
                self.protocol.votekick_cleanup()
            connection.kick(self)
        
        def start_votekick(instigator, target, reason = None):
            protocol = instigator.protocol
            if protocol.votekick_votes_available() <= 0:
                return 'Not enough players on server.'
            elif target is instigator:
                return "You can't votekick yourself."
            elif target.admin:
                return 'Cannot votekick an administrator.'
            elif (target.rights and 'cancel' in target.rights):
                return 'Target has vote cancellation rights.'
            elif protocol.vk_target is not None:
                return 'Votekick already in progress.'
            last = instigator.last_votekick
            if (last is not None and not connection.admin and
            reactor.seconds() - last < protocol.votekick_interval):
                return "You can't start a votekick now."
            # begin votekick

            for player in protocol.players.values():
                player.vk_vote_status = None
            
            instigator.vk_vote_status = True
            protocol.vk_instigator = instigator
            protocol.vk_target = target
            protocol.vk_reason = reason
            if reason is None:
                reason = 'NO REASON GIVEN'
            protocol.irc_say(
                '* %s initiated a votekick against player %s.%s' % (
                instigator.name, target.name,
                ' Reason: %s' % reason if reason else ''))
            protocol.send_chat(
                '%s initiated a VOTEKICK against player %s. Say /y to '
                'agree.' % (instigator.name, target.name),
                    sender = instigator)
            protocol.send_chat('Reason: %s' % reason, sender = instigator)
            instigator.send_chat('You initiated a VOTEKICK against %s. '
                'Say /cancel to stop it at any time.' % target.name)
            instigator.send_chat('Reason: %s' % reason)
            protocol.on_votekick_start()
            protocol.vk_schedule = Schedule(protocol, [
            AlarmLater(protocol.votekick_timeout,
                       seconds=protocol.votekick_time),
            AlarmLater(protocol.votekick_update, seconds=30,
                       loop=True, traversal_required=False)], None,
                        "Votekick %s -> %s" % (instigator.name,
                                               target.name))
            protocol.schedule.queue(protocol.vk_schedule)

    return VotekickProtocol, VotekickConnection
