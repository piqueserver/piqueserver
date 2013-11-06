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

from twisted.internet.reactor import seconds
from scheduler import Scheduler
from commands import name, add, get_player, join_arguments, InvalidPlayer

REQUIRE_REASON = True

S_NO_VOTEKICK = 'No votekick in progress'
S_DEFAULT_REASON = 'NO REASON GIVEN'
S_IN_PROGRESS = 'Votekick already in progress'
S_SELF_VOTEKICK = "You can't votekick yourself"
S_NOT_ENOUGH_PLAYERS = "There aren't enough players to vote"
S_VOTEKICK_IMMUNE = "You can't votekick this player"
S_NOT_YET = "You can't start another votekick yet!"
S_NEED_REASON = 'You must provide a reason for the votekick'
S_CANT_CANCEL = "You didn't start the votekick!"
S_YES = '{player} voted YES'
S_ENDED = 'Votekick for {victim} has ended. {result}'
S_RESULT_TIMED_OUT = 'Votekick timed out'
S_RESULT_CANCELLED = 'Cancelled'
S_RESULT_BANNED = 'Banned by admin'
S_RESULT_KICKED = 'Kicked by admin'
S_RESULT_INSTIGATOR_KICKED = 'Instigator kicked by admin'
S_RESULT_LEFT = '{victim} left during votekick'
S_RESULT_INSTIGATOR_LEFT = 'Instigator {instigator} left'
S_RESULT_PASSED = 'Player kicked'
S_ANNOUNCE_IRC = '* {instigator} started a votekick against player {victim}. ' \
    'Reason: {reason}'
S_ANNOUNCE = '{instigator} started a VOTEKICK against {victim}. Say /Y to agree'
S_ANNOUNCE_SELF = 'You started a votekick against {victim}. Say /CANCEL to ' \
    'stop it'
S_UPDATE = '{instigator} is votekicking {victim}. /Y to vote ({needed} left)'
S_REASON = 'Reason: {reason}'

class VotekickFailure(Exception):
    pass

@name('votekick')
def start_votekick(connection, *args):
    protocol = connection.protocol
    if connection not in protocol.players:
        raise KeyError()
    player = connection
    
    if not args:
        if protocol.votekick:
            # player requested votekick info
            protocol.votekick.send_chat_update(player)
            return
        raise ValueError()
    
    value = args[0]
    try:
        # vanilla aos behavior
        victim = get_player(protocol, '#' + value)
    except InvalidPlayer:
        victim = get_player(protocol, value)
    reason = join_arguments(args[1:])
    
    try:
        # attempt to start votekick
        votekick = Votekick.start(player, victim, reason)
        protocol.votekick = votekick
    except VotekickFailure as err:
        return str(err)

@name('cancel')
def cancel_votekick(connection):
    protocol = connection.protocol
    votekick = protocol.votekick
    if not votekick:
        return S_NO_VOTEKICK
    if connection in protocol.players:
        player = connection
        if (player is not votekick.instigator and not player.admin and
            not player.rights.cancel):
            return S_CANT_CANCEL
    
    votekick.end(S_RESULT_CANCELLED)

@name('y')
def vote_yes(connection):
    protocol = connection.protocol
    if connection not in protocol.players:
        raise KeyError()
    player = connection
    
    votekick = protocol.votekick
    if not votekick:
        return S_NO_VOTEKICK
    
    votekick.vote(player)

add(start_votekick)
add(cancel_votekick)
add(vote_yes)

class Votekick(object):
    duration = 120.0 # 2 minutes
    interval = 2 * 60.0 # 3 minutes
    ban_duration = 15.0
    public_votes = True
    schedule = None
    
    def _get_votes_remaining(self):
        return self.protocol.get_required_votes() - len(self.votes) + 1
    votes_remaining = property(_get_votes_remaining)
    
    @classmethod
    def start(cls, instigator, victim, reason = None):
        protocol = instigator.protocol
        last_votekick = instigator.last_votekick
        reason = reason.strip() if reason else None
        if protocol.votekick:
            raise VotekickFailure(S_IN_PROGRESS)
        elif instigator is victim:
            raise VotekickFailure(S_SELF_VOTEKICK)
        elif protocol.get_required_votes() <= 0:
            raise VotekickFailure(S_NOT_ENOUGH_PLAYERS)
        elif victim.admin or victim.rights.cancel:
            raise VotekickFailure(S_VOTEKICK_IMMUNE)
        elif not instigator.admin and (last_votekick is not None and
            seconds() - last_votekick < cls.interval):
            raise VotekickFailure(S_NOT_YET)
        elif REQUIRE_REASON and not reason:
            raise VotekickFailure(S_NEED_REASON)
        
        result = protocol.on_votekick_start(instigator, victim, reason)
        if result is not None:
            raise VotekickFailure(result)
        
        reason = reason or S_DEFAULT_REASON
        return cls(instigator, victim, reason)
    
    def __init__(self, instigator, victim, reason):
        self.protocol = protocol = instigator.protocol
        self.instigator = instigator
        self.victim = victim
        self.reason = reason
        self.votes = {instigator : True}
        self.ended = False
        
        protocol.irc_say(S_ANNOUNCE_IRC.format(instigator = instigator.name,
            victim = victim.name, reason = self.reason))
        protocol.send_chat(S_ANNOUNCE.format(instigator = instigator.name,
            victim = victim.name), sender = instigator)
        protocol.send_chat(S_REASON.format(reason = self.reason),
            sender = instigator)
        instigator.send_chat(S_ANNOUNCE_SELF.format(victim = victim.name))
        
        schedule = Scheduler(protocol)
        schedule.call_later(self.duration, self.end, S_RESULT_TIMED_OUT)
        schedule.loop_call(30.0, self.send_chat_update)
        self.schedule = schedule
    
    def vote(self, player):
        if self.victim is player:
            return
        elif player in self.votes:
            return
        if self.public_votes:
            self.protocol.send_chat(S_YES.format(player = player.name))
        self.votes[player] = True
        if self.votes_remaining <= 0:
            # vote passed, ban or kick accordingly
            victim = self.victim
            self.end(S_RESULT_PASSED)
            print '%s votekicked' % victim.name
            if self.ban_duration > 0.0:
                victim.ban(self.reason, self.ban_duration)
            else:
                victim.kick(silent = True)
    
    def release(self):
        self.instigator = None
        self.victim = None
        self.votes = None
        if self.schedule:
            self.schedule.reset()
        self.schedule = None
        self.protocol.votekick = None
    
    def end(self, result):
        self.ended = True
        message = S_ENDED.format(victim = self.victim.name, result = result)
        self.protocol.send_chat(message, irc = True)
        if not self.instigator.admin:
            self.instigator.last_votekick = seconds()
        self.protocol.on_votekick_end()
        self.release()
    
    def send_chat_update(self, target = None):
        # send only to target player if provided, otherwise broadcast to server
        target = target or self.protocol
        target.send_chat(S_UPDATE.format(instigator = self.instigator.name,
            victim = self.victim.name, needed = self.votes_remaining))
        target.send_chat(S_REASON.format(reason = self.reason))

def apply_script(protocol, connection, config):
    Votekick.ban_duration = config.get('votekick_ban_duration', 15.0)
    Votekick.public_votes = config.get('votekick_public_votes', True)
    required_percentage = config.get('votekick_percentage', 25.0)
    
    class VotekickProtocol(protocol):
        votekick = None
        
        def get_required_votes(self):
            # votekicks are invalid if this returns <= 0
            player_count = sum(not player.disconnected for player in
                self.players.itervalues()) - 1
            return int(player_count / 100.0 * required_percentage)
        
        def on_map_leave(self):
            if self.votekick:
                self.votekick.release()
            protocol.on_map_leave(self)
        
        def on_ban(self, banee, reason, duration):
            votekick = self.votekick
            if votekick and votekick.victim is self:
                votekick.end(S_RESULT_BANNED)
            protocol.on_ban(self, connection, reason, duration)
        
        def on_votekick_start(self, instigator, victim, reason):
            pass
        
        def on_votekick_end(self):
            pass
    
    class VotekickConnection(connection):
        last_votekick = None
        
        def on_disconnect(self):
            votekick = self.protocol.votekick
            if votekick:
                if votekick.victim is self:
                    # victim leaves, gets votekick ban
                    reason = votekick.reason
                    votekick.end(S_RESULT_LEFT.format(victim = self.name))
                    self.ban(reason, Votekick.ban_duration)
                elif votekick.instigator is self:
                    # instigator leaves, votekick is called off
                    s = S_RESULT_INSTIGATOR_LEFT.format(instigator = self.name)
                    votekick.end(s)
                else:
                    # make sure we still have enough players
                    votekick.votes.pop(self, None)
                    if votekick.votes_remaining <= 0:
                        votekick.end(S_NOT_ENOUGH_PLAYERS)
            connection.on_disconnect(self)
        
        def kick(self, reason = None, silent = False):
            votekick = self.protocol.votekick
            if votekick:
                if votekick.victim is self:
                    votekick.end(S_RESULT_KICKED)
                elif votekick.instigator is self:
                    votekick.end(S_RESULT_INSTIGATOR_KICKED)
            connection.kick(self, reason, silent)
    
    return VotekickProtocol, VotekickConnection