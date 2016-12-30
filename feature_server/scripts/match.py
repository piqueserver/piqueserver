"""
Match script, useful for public matches. Features verbose announcements
on IRC and a custom timer.

Maintainer: mat^2
"""

from twisted.internet import reactor
from twisted.internet.task import LoopingCall

import json
import commands

@commands.admin
@commands.name('timer')
def start_timer(connection, end):
    return connection.protocol.start_timer(int(end) * 60)

@commands.admin
@commands.name('stoptimer')
def stop_timer(connection, end):
    return connection.protocol.stop_timer()

@commands.admin
@commands.name('startrecord')
def start_record(connection):
    connection.protocol.start_record()
    return 'Recording started.'

@commands.admin
@commands.name('stoprecord')
def stop_record(connection):
    connection.protocol.stop_record()
    return 'Recording stopped.'

@commands.admin
@commands.name('saverecord')
def save_record(connection, value):
    if not connection.protocol.save_record(value):
        return 'No record file available.'
    return 'Record saved.'

commands.add(start_timer)
commands.add(stop_timer)
commands.add(start_record)
commands.add(stop_record)
commands.add(save_record)

def apply_script(protocol, connection, config):
    class MatchConnection(connection):
        def on_flag_take(self):
            self.add_message("%s took %s's flag!" %
                (self.printable_name, self.team.other.name.lower()))
            return connection.on_flag_take(self)

        def on_flag_drop(self):
            self.add_message("%s dropped %s's flag!" %
                (self.printable_name, self.team.other.name.lower()))
            return connection.on_flag_drop(self)

        def on_flag_capture(self):
            self.add_message("%s captured %s's flag!" %
                (self.printable_name, self.team.other.name.lower()))
            return connection.on_flag_capture(self)

        def on_kill(self, killer, type, grenade):
            if killer is None:
                killer = self
            self.add_message("%s was killed by %s!" %
                (self.printable_name, killer.printable_name))
            self.protocol.add_kill(self, killer)
            return connection.on_kill(self, killer, type, grenade)

        def add_message(self, value):
            self.protocol.messages.append(value)

    class MatchProtocol(protocol):
        timer_left = None
        timer_call = None
        timer_end = None
        record = None
        def __init__(self, *arg, **kw):
            protocol.__init__(self, *arg, **kw)
            self.messages = []
            self.send_message_loop = LoopingCall(self.display_messages)
            self.send_message_loop.start(3)

        def start_timer(self, end):
            if self.timer_end is not None:
                return 'Timer is running already.'
            self.timer_end = reactor.seconds() + end
            self.send_chat('Timer started, ending in %s minutes' % (end / 60),
                irc = True)
            self.display_timer(True)

        def stop_timer(self):
            if self.timer_call is not None:
                self.timer_call.cancel()
                self.send_chat('Timer stopped.')
                self.timer_call = None
            else:
                return 'No timer in progress.'

        def display_timer(self, silent = False):
            time_left = self.timer_end - reactor.seconds()
            minutes_left = time_left / 60.0
            next_call = 60
            if not silent:
                if time_left <= 0:
                    self.send_chat('Timer ended!', irc = True)
                    self.timer_end = None
                    return
                elif minutes_left <= 1:
                    self.send_chat('%s seconds left' % int(time_left),
                        irc = True)
                    next_call = max(1, int(time_left / 2.0))
                else:
                    self.send_chat('%s minutes left' % int(minutes_left),
                        irc = True)
            self.timer_call = reactor.callLater(next_call, self.display_timer)

        def display_messages(self):
            if not self.messages:
                return
            message = self.messages.pop(0)
            self.irc_say(message)

        # recording

        def add_kill(self, player, killing_player):
            if self.record is None:
                return
            self.get_record(player.name)['deaths'] += 1
            self.get_record(killing_player.name)['kills'] += 1

        def get_record(self, name):
            try:
                return self.record[name]
            except KeyError:
                record = {'deaths' : 0, 'kills' : 0}
                self.record[name] = record
                return record

        def start_record(self):
            self.record = {}

        def stop_record(self):
            self.record = None

        def save_record(self, value):
            if self.record is None:
                return False
            json.dump(self.record, open(value, 'wb'))
            return True

    return MatchProtocol, MatchConnection
