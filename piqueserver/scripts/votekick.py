"""
Allows users to start votekicks

Commands
^^^^^^^^

* ``/votekick <player> <reason>`` start votekick against a player
* ``/y`` votes yes
* ``/togglevotekick or /tvk`` toggles votekicks on/off globally
* ``/togglevotekick or /tvk <player>`` toggles votekicks on/off for specific players
* ``/cancel`` cancels a votekick

Options
^^^^^^^

.. code-block:: guess

    [votekick]
    # percentage of total number of players in the server required to vote to
    # successfully votekick a player
    percentage = 35

    # duration that votekicked player will be banned for
    ban_duration = "30min"

    public_votes = true

.. codeauthor:: James Hofmann a.k.a triplefox
"""


from twisted.internet.reactor import seconds
from piqueserver.scheduler import Scheduler
from piqueserver.commands import (command, admin, get_player, join_arguments,
                                  CommandError, player_only)
from piqueserver.config import config, cast_duration

REQUIRE_REASON = True

S_VOTEKICKING_DISABLED = 'Votekicking disabled'
S_VOTEKICKING_SET = 'Votekicking globally {set}.'
S_VOTEKICK_DISALLOWED = 'You are not allowed to initiate a votekick.'
S_VOTEKICK_USER_SET = 'Votekicking is {set} for {user}.'
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

# register options
VOTEKICK_CONFIG = config.section('votekick')
REQUIRED_PERCENTAGE_OPTION = VOTEKICK_CONFIG.option('percentage', 35.0)
BAN_DURATION_OPTION = VOTEKICK_CONFIG.option('ban_duration', default="30min", cast=cast_duration)
PUBLIC_VOTES_OPTION = VOTEKICK_CONFIG.option('public_votes', True)

class VotekickFailure(Exception):
    pass


@command('votekick')
@player_only
def start_votekick(connection, *args):
    """
    Starts an votekick against a player
    /votekick <player name or id> <reason>
    """
    protocol = connection.protocol
    player = connection

    if not protocol.votekick_enabled:
        return S_VOTEKICKING_DISABLED
    if not player.votekick_enabled:
        return S_VOTEKICK_DISALLOWED

    if not args:
        if protocol.votekick:
            # player requested votekick info
            protocol.votekick.send_chat_update(player)
            return
        raise ValueError("Target player is required")

    value = args[0]
    victim = get_player(protocol, value)
    reason = join_arguments(args[1:])

    try:
        # attempt to start votekick
        votekick = Votekick.start(player, victim, reason)
        protocol.votekick = votekick
    except VotekickFailure as err:
        return str(err)


@command('cancel')
def cancel_votekick(connection):
    """
    Cancels an ongoing vote
    /cancel
    """
    protocol = connection.protocol
    votekick = protocol.votekick
    if not votekick:
        return S_NO_VOTEKICK
    if connection in protocol.players.values():
        player = connection
        if (player is not votekick.instigator and not player.admin and
                not player.rights.cancel):
            return S_CANT_CANCEL

    votekick.end(S_RESULT_CANCELLED)


@command('y')
@player_only
def vote_yes(connection):
    """
    Vote yes on an ongoing vote
    /y
    """
    player = connection

    votekick = connection.protocol.votekick
    if not votekick:
        return S_NO_VOTEKICK

    votekick.vote(player)


@command('tvk', admin_only=True)
def togglevotekick(connection, *args):
    """
    Toggles votekicking for a player or the whole server
    /tvk <player> or /tvk
    """
    protocol = connection.protocol
    if len(args) == 0:
        protocol.votekick_enabled = not protocol.votekick_enabled
        return S_VOTEKICKING_SET.format(
            set=('enabled' if protocol.votekick_enabled else 'disabled'))
    try:
        player = get_player(protocol, args[0])
    except CommandError:
        return 'Invalid Player'
    player.votekick_enabled = not player.votekick_enabled
    return S_VOTEKICK_USER_SET.format(user=player.name, set=(
        'enabled' if player.votekick_enabled else 'disabled'))


class Votekick:
    timeout = 120.0  # 2 minutes
    interval = 120.0  # 2 minutes
    ban_duration = BAN_DURATION_OPTION.get()
    public_votes = PUBLIC_VOTES_OPTION.get()
    schedule = None

    @property
    def votes_remaining(self) -> int:
        return self.protocol.get_required_votes() - len(self.votes) + 1

    @classmethod
    def start(cls, instigator, victim, reason=None):
        protocol = instigator.protocol
        last_votekick = instigator.last_votekick
        reason = reason.strip() if reason else None
        if protocol.votekick:
            raise VotekickFailure(S_IN_PROGRESS)
        elif instigator is victim:
            raise VotekickFailure(S_SELF_VOTEKICK)
        elif protocol.get_required_votes() <= 0:
            raise VotekickFailure(S_NOT_ENOUGH_PLAYERS)
        elif victim.admin or victim.rights.cancel or victim.local:
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
        self.votes = {instigator: True}
        self.ended = False

        protocol.irc_say(
            S_ANNOUNCE_IRC.format(
                instigator=instigator.name,
                victim=victim.name,
                reason=self.reason))
        protocol.send_chat(
            S_ANNOUNCE.format(
                instigator=instigator.name,
                victim=victim.name),
            sender=instigator)
        protocol.send_chat(S_REASON.format(reason=self.reason),
                           sender=instigator)
        instigator.send_chat(S_ANNOUNCE_SELF.format(victim=victim.name))

        schedule = Scheduler(protocol)
        schedule.call_later(self.timeout, self.end, S_RESULT_TIMED_OUT)
        schedule.loop_call(30.0, self.send_chat_update)
        self.schedule = schedule

    def vote(self, player):
        if self.victim is player:
            return
        elif player in self.votes:
            return
        if self.public_votes:
            self.protocol.send_chat(S_YES.format(player=player.name))
        self.votes[player] = True
        if self.votes_remaining <= 0:
            # vote passed, ban or kick accordingly
            victim = self.victim
            self.end(S_RESULT_PASSED)
            print(victim.name, 'votekicked')
            if self.ban_duration > 0.0:
                victim.ban(self.reason, self.ban_duration)
            else:
                victim.kick(silent=True)

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
        message = S_ENDED.format(victim=self.victim.name, result=result)
        self.protocol.send_chat(message, irc=True)
        if not self.instigator.admin:
            self.instigator.last_votekick = seconds()
        self.protocol.on_votekick_end()
        self.release()

    def send_chat_update(self, target=None):
        # send only to target player if provided, otherwise broadcast to server
        target = target or self.protocol
        target.send_chat(
            S_UPDATE.format(
                instigator=self.instigator.name,
                victim=self.victim.name,
                needed=self.votes_remaining))
        target.send_chat(S_REASON.format(reason=self.reason))


def apply_script(protocol, connection, config):

    class VotekickProtocol(protocol):
        votekick = None
        votekick_enabled = True

        def get_required_votes(self):
            # votekicks are invalid if this returns <= 0
            player_count = sum(not player.disconnected and not player.local
                               for player in self.players.values()) - 1
            return int(player_count / 100.0 * REQUIRED_PERCENTAGE_OPTION.get())

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
        votekick_enabled = True

        def on_disconnect(self):
            votekick = self.protocol.votekick
            if votekick:
                if votekick.victim is self:
                    # victim leaves, gets votekick ban
                    reason = votekick.reason
                    votekick.end(S_RESULT_LEFT.format(victim=self.name))
                    self.ban(reason, Votekick.ban_duration)
                elif votekick.instigator is self:
                    # instigator leaves, votekick is called off
                    s = S_RESULT_INSTIGATOR_LEFT.format(instigator=self.name)
                    votekick.end(s)
                else:
                    # make sure we still have enough players
                    votekick.votes.pop(self, None)
                    if votekick.votes_remaining <= 0:
                        votekick.end(S_NOT_ENOUGH_PLAYERS)
            connection.on_disconnect(self)

        def kick(self, reason=None, silent=False):
            votekick = self.protocol.votekick
            if votekick:
                if votekick.victim is self:
                    votekick.end(S_RESULT_KICKED)
                elif votekick.instigator is self:
                    votekick.end(S_RESULT_INSTIGATOR_KICKED)
            connection.kick(self, reason, silent)

    return VotekickProtocol, VotekickConnection
