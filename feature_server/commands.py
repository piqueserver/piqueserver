# Copyright (c) Mathias Kaerlev 2011.

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

import inspect

class InvalidPlayer(Exception):
    pass

class InvalidTeam(Exception):
    pass

def admin(func):
    def new_func(connection, *arg, **kw):
        if not connection.admin:
            return 'No administrator rights!'
        func(connection, *arg, **kw)
    new_func.func_name = func.func_name
    return new_func

def name(name):
    def dec(func):
        func.func_name = name
        return func
    return dec

def get_player(connection, value):
    try:
        if value.startswith('#'):
            value = int(value[1:])
            return connection.protocol.players[value][0]
        value = value.lower()
        for player in connection.protocol.players.values():
            if player.name.lower().count(value):
                return player
    except (KeyError, IndexError, ValueError):
        pass
    raise InvalidPlayer()

def get_team(connection, value):
    value = value.lower()
    if value == 'blue':
        return connection.protocol.blue_team
    elif value == 'green':
        return connection.protocol.green_team
    raise InvalidTeam()

def join_arguments(arg, default = None):
    if not arg:
        return default
    return ' '.join(arg)

@admin
def kick(connection, value, *arg):
    reason = join_arguments(arg)
    player = get_player(connection, value)
    player.kick(reason)

@admin
def ban(connection, value, *arg):
    reason = join_arguments(arg)
    player = get_player(connection, value)
    player.ban(reason)

@admin
def say(connection, *arg):
    value = ' '.join(arg)
    connection.protocol.send_chat(value)

@admin
def kill(connection, value):
    player = get_player(connection, value)
    player.kill()
    connection.protocol.send_chat('%s killed %s' % (connection.name, 
        player.name))

@admin
def heal(connection, value):
    player = get_player(connection, value)
    player.refill()
    connection.protocol.send_chat('%s was healed by %s' % (player.name,
        connection.name))

def votekick(connection, value, *arg):
    reason = join_arguments(arg)
    player = get_player(connection, value)
    player.votekick(connection, reason)

def rules(connection):
    lines = connection.protocol.rules
    if lines is None:
        return
    connection.send_lines(lines)

def help(connection):
    """
    This help
    """
    names = [command.func_name for command in command_list]
    return 'Available commands: %s' % (', '.join(names))

def login(connection, password):
    """
    Login as admin
    """
    passwords = connection.protocol.admin_passwords
    if password in passwords:
        connection.admin = True
        connection.protocol.send_chat('%s logged in as admin' % connection.name)
        return None
    return 'Invalid password!'

def pm(connection, value, *arg):
    player = get_player(connection, value)
    message = join_arguments(arg)
    player.send_chat('PM from %s: %s' % (connection.name, message))
    return 'PM sent to %s' % player.name

@admin
def lock(connection, value):
    team = get_team(connection, value)
    team.locked = True
    connection.protocol.send_chat('%s team is now locked' % team.name)

@admin
def unlock(connection, value):
    team = get_team(connection, value)
    team.locked = False
    connection.protocol.send_chat('%s team is now unlocked' % team.name)

@name('setbalance')
@admin
def set_balance(connection, value):
    try:
        value = int(value)
    except ValueError:
        return 'Invalid value %r. Use 0 for off, 1 and up for on' % value
    protocol = connection.protocol
    protocol.balanced_teams = value
    protocol.send_chat('Balanced teams set to %s' % value)

@name('togglebuild')
@admin
def toggle_build(connection):
    value = not connection.protocol.building
    connection.protocol.building = value
    connection.protocol.send_chat('Building has been toggled %s!' % (
        ['OFF', 'ON'][int(value)]))
    
@name('togglekill')
@admin
def toggle_kill(connection):
    value = not connection.protocol.killing
    connection.protocol.killing = value
    connection.protocol.send_chat('Killing has been toggled %s!' % (
        ['OFF', 'ON'][int(value)]))

@name('toggleteamkill')
@admin
def toggle_teamkill(connection):
    value = not connection.protocol.friendly_fire
    connection.protocol.friendly_fire = value
    connection.protocol.send_chat('Friendly fire has been toggled %s!' % (
        ['OFF', 'ON'][int(value)]))

@admin
def mute(connection, value):
    player = get_player(connection, value)
    player.mute = True
    connection.protocol.send_chat('%s has been muted by %s' % (
        connection.name, player.name))

@admin
def unmute(connection, value):
    player = get_player(connection, value)
    player.mute = False
    connection.protocol.send_chat('%s has been unmuted by %s' % (
        connection.name, player.name))
    
command_list = [
    help,
    pm,
    login,
    kick,
    votekick,
    ban,
    mute,
    unmute,
    say,
    kill,
    heal,
    lock,
    unlock,
    set_balance,
    rules,
    toggle_build,
    toggle_kill,
    toggle_teamkill
]

commands = {}

for command_func in command_list:
    commands[command_func.func_name] = command_func

def handle_command(connection, command, parameters):
    command = command.lower()
    try:
        command_func = commands[command]
    except KeyError:
        return 'Invalid command'
    try:
        return command_func(connection, *parameters)
    except TypeError:
        return 'Invalid number of arguments for %s' % command
    except InvalidPlayer:
        return 'No such player'
    except InvalidTeam:
        return 'Invalid team specifier'
    except ValueError:
        return 'Invalid parameters'