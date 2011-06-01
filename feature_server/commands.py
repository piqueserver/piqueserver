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
    new_func.admin = True
    return new_func

def name(name):
    def dec(func):
        func.func_name = name
        return func
    return dec

def get_player(protocol, value):
    try:
        if value.startswith('#'):
            value = int(value[1:])
            return protocol.players[value][0]
        players = protocol.players
        try:
            return players[value][0]
        except KeyError:
            value = value.lower()
            for player in players.values():
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
    player = get_player(connection.protocol, value)
    player.kick(reason)

@admin
def ban(connection, value, *arg):
    reason = join_arguments(arg)
    player = get_player(connection.protocol, value)
    player.ban(reason)

@admin
def say(connection, *arg):
    value = ' '.join(arg)
    connection.protocol.send_chat(value)
    connection.protocol.irc_say(value)

@admin
def kill(connection, value):
    player = get_player(connection.protocol, value)
    player.kill()
    message = '%s killed %s' % (connection.name, player.name)
    connection.protocol.send_chat(message, irc = True)

@admin
def heal(connection, player = None):
    if player is not None:
        player = get_player(connection.protocol, player)
        message = '%s was healed by %s' % (player.name, connection.name)
    else:
        player = connection
        message = '%s was healed' % (connection.name)
    player.refill()
    connection.protocol.send_chat(message, irc = True)

def votekick(connection, value):
    player = get_player(connection.protocol, value)
    return connection.protocol.start_votekick(connection, player)

@name('y')
def vote_yes(connection):
    connection.protocol.votekick(connection, True)

@name('n')
def vote_no(connection):
    connection.protocol.votekick(connection, False)

@name('cancel')
def cancel_vote(connection):
    return connection.protocol.cancel_votekick(connection)

def rules(connection):
    lines = connection.protocol.rules
    if lines is None:
        return
    connection.send_lines(lines)

def help(connection):
    """
    This help
    """
    names = [command.func_name for command in command_list
        if hasattr(command, 'admin') in (connection.admin, False)]
    return 'Available commands: %s' % (', '.join(names))

def login(connection, password):
    """
    Login as admin
    """
    passwords = connection.protocol.admin_passwords
    if password in passwords:
        connection.admin = True
        message = '%s logged in as admin' % connection.name
        connection.protocol.send_chat(message, irc = True)
        return None
    if connection.login_retries is None:
        connection.login_retries = connection.protocol.login_retries - 1
    if not connection.login_retries:
        connection.kick('Ran out of login attempts')
        return
    return 'Invalid password - you have %s tries left' % (
        connection.login_retries)

def pm(connection, value, *arg):
    player = get_player(connection.protocol, value)
    message = join_arguments(arg)
    player.send_chat('PM from %s: %s' % (connection.name, message))
    return 'PM sent to %s' % player.name

def follow(connection, value):
    """Follow a player; on your next spawn, you'll spawn at their position, similar to the squad spawning feature
       of Battlefield."""
    player = get_player(connection.protocol, value)
    curfollowed = player.get_followers()
    # TODO - server option for follow limits
    followlimit = connection.protocol.max_followers
    if player.player_id==connection.player_id:
        return "You can't follow yourself!"
    if connection.team!=player.team:
        return '%s is not on your team.' % (player.name)
    if player.player_id==connection.follow:
        return "You're already following %s" % (player.name)
    if len(curfollowed)>=followlimit:
        return '%s has too many followers (limit %s)' % (player.name, followlimit)
    connection.set_follower(player.player_id)
    return 'You will now spawn where %s is.' % (player.name)

def unfollow(connection):
    connection.set_follower(None)
    return 'You are no longer following players.'

@admin
def lock(connection, value):
    team = get_team(connection, value)
    team.locked = True
    connection.protocol.send_chat('%s team is now locked' % team.name)
    connection.protocol.irc_say('* %s locked %s team' % (connection.name, 
        team.name))

@admin
def unlock(connection, value):
    team = get_team(connection, value)
    team.locked = False
    connection.protocol.send_chat('%s team is now unlocked' % team.name)
    connection.protocol.irc_say('* %s unlocked %s team' % (connection.name, 
        team.name))

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
    connection.protocol.irc_say('* %s set balanced teams to %s' % (
        connection.name, value))

@name('togglebuild')
@admin
def toggle_build(connection):
    value = not connection.protocol.building
    connection.protocol.building = value
    on_off = ['OFF', 'ON'][int(value)]
    connection.protocol.send_chat('Building has been toggled %s!' % on_off)
    connection.protocol.irc_say('* %s toggled building %s' % (connection.name, 
        on_off))
    
@name('togglekill')
@admin
def toggle_kill(connection):
    value = not connection.protocol.killing
    connection.protocol.killing = value
    on_off = ['OFF', 'ON'][int(value)]
    connection.protocol.send_chat('Killing has been toggled %s!' % on_off)
    connection.protocol.irc_say('* %s toggled killing %s' % (connection.name, 
        on_off))

@name('toggleteamkill')
@admin
def toggle_teamkill(connection):
    value = not connection.protocol.friendly_fire
    connection.protocol.friendly_fire = value
    on_off = ['OFF', 'ON'][int(value)]
    connection.protocol.send_chat('Friendly fire has been toggled %s!' % on_off)
    connection.protocol.irc_say('* %s toggled friendly fire %s' % (
        connection.name, on_off))

@admin
def mute(connection, value):
    player = get_player(connection.protocol, value)
    player.mute = True
    message = '%s has been muted by %s' % (player.name, connection.name)
    connection.protocol.send_chat(message, irc = True)

@admin
def unmute(connection, value):
    player = get_player(connection.protocol, value)
    player.mute = False
    message = '%s has been unmuted by %s' % (player.name, connection.name)
    connection.protocol.send_chat(message, irc = True)

from pyspades.server import position_data

@admin
def teleport(connection, player1, player2 = None):
    player1 = get_player(connection.protocol, player1)
    if player2 is not None:
        player, target = player1, get_player(connection.protocol, player2)
        message = '%s teleported %s to %s' % (connection.name, player.name, 
            target.name)
    else:
        player, target = connection, player1
        message = '%s teleported to %s' % (connection.name, target.name)
    
    position_data.x = target.position.x
    position_data.y = target.position.y
    position_data.z = target.position.z
    position_data.player_id = player.player_id
    player.send_contained(position_data)
    connection.protocol.send_chat(message, irc = True)

@admin
def god(connection, value = None):
    if value is not None:
        connection = get_player(connection.protocol, value)
    connection.god = not connection.god
    if connection.god:
        message = '%s entered GOD MODE!' % connection.name
    else:
        message = '%s returned to being a mere human.' % connection.name
    connection.protocol.send_chat(message, irc = True)

@admin
def reset_game(connection):
    connection.reset_game()
    connection.protocol.send_chat('Game has been reset by %s' % (connection.name), irc = True)
    
command_list = [
    help,
    pm,
    login,
    kick,
    votekick,
    vote_yes,
    vote_no,
    cancel_vote,
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
    toggle_teamkill,
    teleport,
    god,
    follow,
    unfollow,
    reset_game
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