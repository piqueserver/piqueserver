"""
Allows muting players for a set amount of time.

Commands
^^^^^^^^

* ``/tm <player> <seconds> <reason>`` mute a player for set amount of time *admin only*

.. note::
  Default time 5 minutes, default reason None

.. codeauthor: topologist
"""

from piqueserver.scheduler import Scheduler
from piqueserver.commands import command, get_player, join_arguments


@command('tm', admin_only=True)
def timed_mute(connection, *args):
    protocol = connection.protocol
    if len(args) < 3:
        return '/tm <nick> <time> <reason>'

    nick = args[0]
    time = int(args[1])
    reason = join_arguments(args[2:])
    player = get_player(protocol, nick)

    if time < 0:
        raise ValueError("Time cannot be < 0")

    if not player.mute:
        TimedMute(player, time, reason)
    else:
        return '%s is already muted!' % nick


class TimedMute:
    player = None
    time = None

    def __init__(self, player, time=300, reason='None'):
        if time == 0:
            player.mute = True
            player.protocol.send_chat(
                '%s was muted indefinitely (Reason: %s)' %
                (player.name, reason), irc=True)
            return

        schedule = Scheduler(player.protocol)
        schedule.call_later(time, self.end)
        player.mute_schedule = schedule

        player.protocol.send_chat(
            '%s was muted for %s seconds (Reason: %s)' %
            (player.name, time, reason), irc=True)
        player.mute = True

        self.player = player
        self.time = time

    def end(self):
        self.player.mute = False
        message = '%s was unmuted after %s seconds' % (
            self.player.name, self.time)
        self.player.protocol.send_chat(message, irc=True)


def apply_script(protocol, connection, config):
    class TimedMuteConnection(connection):
        mute_schedule = None

        def on_disconnect(self):
            if self.mute_schedule:
                del self.mute_schedule
            connection.on_disconnect(self)

    return protocol, TimedMuteConnection
