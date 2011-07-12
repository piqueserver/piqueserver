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

from pyspades.constants import *

class InvalidPlayer(Exception):
    pass

class InvalidTeam(Exception):
    pass

def admin(func):
    def new_func(connection, *arg, **kw):
        if not connection.admin:
            return 'No administrator rights!'
        return func(connection, *arg, **kw)
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

def test(connection):
    connection.set_options(team = connection.team.other, 
        weapon = int(not connection.weapon))

@admin
def kick(connection, value, *arg):
    reason = join_arguments(arg)
    player = get_player(connection.protocol, value)
    player.kick(reason)

@admin
def ban(connection, value, *arg):
    duration = None
    if len(arg):
        try:
            duration = int(arg[0])
            arg = arg[1:]
        except (IndexError, ValueError):
            pass
    if duration is None:
        if len(arg)>0 and arg[0] == "perma":
            arg = arg[1:]
        else:
            duration = connection.protocol.default_ban_time
    reason = join_arguments(arg)
    player = get_player(connection.protocol, value)
    player.ban(reason, duration)

@admin
def unban(connection, ip):
    try:
        connection.protocol.remove_ban(ip)
        return 'IP unbanned.'
    except KeyError:
        return 'IP not found in ban list.'

@name('undoban')
@admin
def undo_ban(connection, *arg):
    if len(connection.protocol.bans)>0:
        result = connection.protocol.bans.pop()
        connection.protocol.save_bans()
        return ('Ban for %s undone.' % result[0])
    else:
        return 'No bans to undo.'

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
        if connection not in connection.protocol.players:
            raise ValueError()
        player = connection
        message = '%s was healed' % (connection.name)
    player.refill()
    connection.protocol.send_chat(message, irc = True)

def votekick(connection, value, *arg):
    reason = join_arguments(arg)
    if connection not in connection.protocol.players:
        raise KeyError()
    player = None
    try:
        player = get_player(connection.protocol, '#' + value)
    except InvalidPlayer:
        player = get_player(connection.protocol, value)
    return connection.protocol.start_votekick(connection, player, reason)

@name('y')
def vote_yes(connection):
    if connection not in connection.protocol.players:
        raise KeyError()
    return connection.protocol.votekick(connection)

@name('cancel')
def cancel_vote(connection):
    return connection.protocol.cancel_votekick(connection)

def rules(connection):
    if connection not in connection.protocol.players:
        raise KeyError()
    lines = connection.protocol.rules
    if lines is None:
        return
    connection.send_lines(lines)

def help(connection):
    """
    This help
    """
    if connection.protocol.help is not None and not connection.admin:
        connection.send_lines(connection.protocol.help)
    else:
        names = [command.func_name for command in command_list
            if hasattr(command, 'admin') in (connection.admin, False)]
        return 'Available commands: %s' % (', '.join(names))

def login(connection, password):
    """
    Login as admin
    """
    if connection not in connection.protocol.players:
        raise KeyError()
    passwords = connection.protocol.admin_passwords
    if password in passwords:
        connection.admin = True
        connection.speedhack_detect = False
        message = '%s logged in as admin' % connection.name
        connection.protocol.send_chat(message, irc = True)
        return None
    if connection.login_retries is None:
        connection.login_retries = connection.protocol.login_retries - 1
    else:
        connection.login_retries -= 1
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

def send_unfollow_message(connection):
    if connection.follow == "attack":
        return 'You are no longer an attacker.'
    else:        
        connection.follow.send_chat('%s is no longer following you.' %
                                connection.name)
        return 'You are no longer following %s.' % connection.follow.name

def follow(connection, player = None):
    """Follow a player; on your next spawn, you'll spawn at their position,
        similar to the squad spawning feature of Battlefield."""
    if connection not in connection.protocol.players:
        raise KeyError()
    if not connection.protocol.max_followers:
        raise KeyError()
    
    # TODO  make "attack" case-insensitive
    #       move this feature into a script

    if player is None:
        if connection.follow is None:
            return ("You aren't following anybody. To follow, say "
                    "/follow <nickname> or /follow attack")
        else:
            connection.respawn_time = connection.protocol.respawn_time
            confirmation = send_unfollow_message(connection)
            connection.follow = None
            return confirmation
    if player == "attack" and (connection.protocol.follow_attack or
                               connection.protocol.follow_attack == "auto"):
        if connection.follow == "attack":
            return "You're already an attacker."
        else:
            if connection.follow is not None:
                connection.send_chat(send_unfollow_message(connection))
            connection.follow = "attack"
            connection.respawn_time = connection.protocol.follow_respawn_time
            return ("You are now an attacker and will spawn with players "
                    "close to the enemy.")
    
    player = get_player(connection.protocol, player)
    if connection == player:
        return "You can't follow yourself!"
    if not connection.team == player.team:
        return '%s is not on your team.' % player.name
    if connection.follow == player:
        return "You're already following %s" % player.name
    if not player.followable:
        return "%s doesn't want to be followed." % player.name
    if len(player.get_followers()) >= connection.protocol.max_followers:
        return '%s has too many followers!' % player.name
    if connection.follow is not None:
        connection.send_chat(send_unfollow_message(connection))
    connection.follow = player
    connection.respawn_time = connection.protocol.follow_respawn_time
    player.send_chat('%s is now following you.' % connection.name)
    return ('Next time you die you will spawn where %s is. To stop, type /follow' %
        player.name)

@name('nofollow')
def no_follow(connection):
    if connection not in connection.protocol.players:
        raise KeyError()
    if not connection.protocol.max_followers:
        raise KeyError()
    connection.followable = not connection.followable
    if not connection.followable:
        connection.drop_followers()
    return 'Teammates will %s be able to follow you.' % (
        'now' if connection.followable else 'no longer')

def streak(connection):
    if connection not in connection.protocol.players:
        raise KeyError()
    return ('Your current kill streak is %s. Best is %s kills.' %
        (connection.streak, connection.best_streak))
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

@admin
def switch(connection, value = None):
    if value is not None:
        connection = get_player(connection.protocol, value)
    elif connection not in connection.protocol.players:
        raise ValueError()
    connection.follow = None
    connection.drop_followers()
    connection.respawn_time = connection.protocol.respawn_time
    connection.team = connection.team.other
    connection.kill()
    connection.protocol.send_chat('%s has switched teams' % connection.name,
        irc = True)

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

@admin
def teleport(connection, player1, player2 = None):
    player1 = get_player(connection.protocol, player1)
    if player2 is not None:
        player, target = player1, get_player(connection.protocol, player2)
        message = '%s teleported %s to %s' % (connection.name, player.name, 
            target.name)
    else:
        if connection not in connection.protocol.players:
            raise ValueError()
        player, target = connection, player1
        message = '%s teleported to %s' % (connection.name, target.name)

    # set location!
    player.set_location(target.get_location())
    connection.protocol.send_chat(message, irc = True)

@admin
def tp(connection, player1, player2 = None):
    teleport(connection, player1, player2)

from pyspades.common import coordinates

@admin
def goto(connection, value):
    if connection not in connection.protocol.players:
        raise KeyError()
    x, y = coordinates(value)
    x += 32
    y += 32
    connection.set_location((x, y, connection.protocol.map.get_height(x, y) - 2))
    message = '%s teleported to location %s' % (connection.name, value.upper())
    connection.protocol.send_chat(message, irc = True)

@admin
def god(connection, value = None):
    if value is not None:
        connection = get_player(connection.protocol, value)
    elif connection not in connection.protocol.players:
        raise ValueError()
    connection.god = not connection.god
    if connection.god:
        message = '%s entered GOD MODE!' % connection.name
    else:
        message = '%s returned to being a mere human.' % connection.name
    connection.protocol.send_chat(message, irc = True)

@admin
def ip(connection, value = None):
    if value is None:
        if connection not in connection.protocol.players:
            raise ValueError()
        player = connection
    else:
        player = get_player(connection.protocol, value)
    return 'The IP of %s is %s' % (player.name, player.address[0])

@name ('resetgame')
@admin
def reset_game(connection):
    resetting_player = connection
    # irc compatibility
    if resetting_player not in connection.protocol.players:
        for player in connection.protocol.players.values():
            resetting_player = player
            if player.admin:
                break
        if resetting_player is connection:
            return
    connection.protocol.reset_game(resetting_player)
    connection.protocol.on_game_end(resetting_player)
    connection.protocol.send_chat('Game has been reset by %s' % connection.name,
        irc = True)

def ping(connection, value = None):
    if value is None:
        if connection not in connection.protocol.players:
            raise ValueError()
        player = connection
    else:
        player = get_player(connection.protocol, value)
    ping = int(player.latency * 1000) or 0
    if value is None:
        return ('Your ping is %s ms. Lower ping is better, with ideal values '
            'around 50-150' % ping)
    return "%s's ping is %s ms" % (player.name, ping)

def intel(connection):
    if connection not in connection.protocol.players:
        raise KeyError()
    flag = connection.team.other.flag
    if flag.player is not None:
        if flag.player is connection:
            return "You have the enemy intel, return to base!"
        else:
            return "%s has the enemy intel!" % flag.player.name
    return "Nobody in your team has the enemy intel."
    
command_list = [
    help,
    pm,
    login,
    kick,
    votekick,
    vote_yes,
    cancel_vote,
    intel,
    ip,
    ban,
    unban,
    undo_ban,
    mute,
    unmute,
    say,
    kill,
    heal,
    lock,
    unlock,
    switch,
    set_balance,
    rules,
    toggle_build,
    toggle_kill,
    toggle_teamkill,
    teleport,
    tp,
    goto,
    god,
    follow,
    no_follow,
    streak,
    reset_game,
    ping,
    test
]

commands = {}

for command_func in command_list:
    commands[command_func.func_name] = command_func

def add(func, name = None):
    """
    Function to add a command from scripts
    """
    if name is None:
        name = func.func_name
    commands[name.lower()] = func

def handle_command(connection, command, parameters):
    command = command.lower()
    try:
        command_func = commands[command]
    except KeyError:
        return # 'Invalid command'
    try:
        return command_func(connection, *parameters)
    except KeyError:
        return # 'Invalid command'
    except TypeError:
        return 'Invalid number of arguments for %s' % command
    except InvalidPlayer:
        return 'No such player'
    except InvalidTeam:
        return 'Invalid team specifier'
    except ValueError:
        return 'Invalid parameters'