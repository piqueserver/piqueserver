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
from pyspades.common import prettify_timespan

class InvalidPlayer(Exception):
    pass

class InvalidTeam(Exception):
    pass

def admin(func):
    def new_func(connection, *arg, **kw):
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
            return protocol.players[value]
        players = protocol.players
        try:
            return players[value]
        except KeyError:
            value = value.lower()
            ret = None
            for player in players.values():
                name = player.name.lower()
                if name == value:
                    return player
                if name.count(value):
                    ret = player
            if ret is not None:
                return ret
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

def get_ban_arguments(connection, arg):
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
    return duration, reason

@admin
def ban(connection, value, *arg):
    duration, reason = get_ban_arguments(connection, arg)
    player = get_player(connection.protocol, value)
    player.ban(reason, duration)

from pyspades.ipaddr import IPNetwork

@admin
def banip(connection, ip, *arg):
    duration, reason = get_ban_arguments(connection, arg)
    try:
        net = IPNetwork(ip)
        connection.protocol.add_ban(ip, reason, duration)
        reason = ': ' + reason if reason is not None else ''
        duration = duration or None
        if duration is None:
            return 'IP/network %s permabanned%s' % (ip, reason)
        else:
            return 'IP/network %s banned for %s%s' % (ip,
                prettify_timespan(duration * 60), reason)
    except:
        return 'Invalid IP address/network.'

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
    for user_type, passwords in connection.protocol.passwords.iteritems():
        if password in passwords:
            if connection.user_types is None:
                connection.user_types = set()
                connection.rights = set()
            if user_type in connection.user_types:
                return "You're already logged in as %s" % user_type
            connection.user_types.update(user_type)
            if user_type in rights:
                connection.rights.update(rights[user_type])
            return connection.on_user_login(user_type)
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
    connection.respawn_time = connection.protocol.respawn_time
    connection.on_team_leave()
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
def toggle_build(connection, player = None):
    if player is not None:
        player = get_player(connection.protocol, player)
        value = not player.building
        player.building = value
        msg = '%s can build again' if value else '%s is disabled from building'
        connection.protocol.send_chat(msg % player.name)
        connection.protocol.irc_say('* %s %s building for %s' % (connection.name,
            ['disabled', 'enabled'][int(value)], player.name))
        return
    value = not connection.protocol.building
    connection.protocol.building = value
    on_off = ['OFF', 'ON'][int(value)]
    connection.protocol.send_chat('Building has been toggled %s!' % on_off)
    connection.protocol.irc_say('* %s toggled building %s' % (connection.name, 
        on_off))
    
@name('togglekill')
@admin
def toggle_kill(connection, player = None):
    if player is not None:
        player = get_player(connection.protocol, player)
        value = not player.killing
        player.killing = value
        msg = '%s can kill again' if value else '%s is disabled from killing'
        connection.protocol.send_chat(msg % player.name)
        connection.protocol.irc_say('* %s %s killing for %s' % (connection.name,
            ['disabled', 'enabled'][int(value)], player.name))
        return
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
    if player.mute:
        return '%s is already muted' % player.name
    player.mute = True
    message = '%s has been muted by %s' % (player.name, connection.name)
    connection.protocol.send_chat(message, irc = True)

@admin
def unmute(connection, value):
    player = get_player(connection.protocol, value)
    if not player.mute:
        return '%s is not muted' % player.name
    player.mute = False
    message = '%s has been unmuted by %s' % (player.name, connection.name)
    connection.protocol.send_chat(message, irc = True)

def deaf(connection, value = None):
    if value is not None:
        if not connection.admin and 'deaf' not in connection.rights:
            return 'No administrator rights!'
        connection = get_player(connection.protocol, value)
    message = '%s deaf.' % ('now' if not connection.deaf else 'no longer')
    connection.protocol.irc_say('%s is %s' % (connection.name, message))
    message = "You're " + message
    if connection.deaf:
        connection.deaf = False
        connection.send_chat(message)
    else:
        connection.send_chat(message)
        connection.deaf = True

@name('globalchat')
@admin
def global_chat(connection):
    connection.protocol.global_chat = not connection.protocol.global_chat
    connection.protocol.send_chat('Global chat %s' % ('enabled' if
        connection.protocol.global_chat else 'disabled'), irc = True)

@admin
def teleport(connection, player1, player2 = None, silent = False):
    player1 = get_player(connection.protocol, player1)
    if player2 is not None:
        if connection.admin or 'teleport_other' in connection.rights:
            player, target = player1, get_player(connection.protocol, player2)
            silent = silent or player.invisible
            message = ('%s ' + ('silently ' if silent else '') + 'teleported '
                '%s to %s')
            message = message % (connection.name, player.name, target.name)
        else:
            return 'No administrator rights!'
    else:
        if connection not in connection.protocol.players:
            raise ValueError()
        player, target = connection, player1
        silent = silent or player.invisible
        message = '%s ' + ('silently ' if silent else '') + 'teleported to %s'
        message = message % (player.name, target.name)
    player.set_location(target.get_location())
    if silent:
        connection.protocol.irc_say('* ' + message)
    else:
        connection.protocol.send_chat(message, irc = True)

@admin
def tp(connection, player1, player2 = None):
    teleport(connection, player1, player2)

@admin
def tpsilent(connection, player1, player2 = None):
    teleport(connection, player1, player2, silent = True)

from pyspades.common import coordinates, to_coordinates

@name('goto')
@admin
def go_to(connection, value):
    if connection not in connection.protocol.players:
        raise KeyError()
    move(connection, connection.name, value, silent = connection.invisible)

@admin
def move(connection, player, value, silent = False):
    player = get_player(connection.protocol, player)
    x, y = coordinates(value)
    x += 32
    y += 32
    player.set_location((x, y, connection.protocol.map.get_height(x, y) - 2))
    if connection is player:
        message = ('%s ' + ('silently ' if silent else '') + 'teleported to '
            'location %s')
        message = message % (player.name, value.upper())
    else:
        message = ('%s ' + ('silently ' if silent else '') + 'teleported %s '
            'to location %s')
        message = message % (connection.name, player.name, value.upper())
    if silent:
        connection.protocol.irc_say('* ' + message)
    else:
        connection.protocol.send_chat(message, irc = True)    

@admin
def where(connection, value = None):
    if value is not None:
        connection = get_player(connection.protocol, value)
    elif connection not in connection.protocol.players:
        raise ValueError()
    x, y, z = connection.get_location()
    return '%s is in %s (%s, %s, %s)' % (connection.name,
        to_coordinates(x, y), int(x), int(y), int(z))

@admin
def god(connection, value = None):
    if value is not None:
        connection = get_player(connection.protocol, value)
    elif connection not in connection.protocol.players:
        raise ValueError()
    connection.god = not connection.god
    if connection.protocol.set_god_build:
        connection.god_build = connection.god
    else:
        connection.god_build = False
    if connection.god:
        message = '%s entered GOD MODE!' % connection.name
    else:
        message = '%s returned to being a mere human.' % connection.name
    connection.protocol.send_chat(message, irc = True)

@name('godbuild')
@admin
def god_build(connection, player = None):
    if player is not None:
        player = get_player(connection.protocol, player)
    elif connection not in connection.protocol.players:
        raise ValueError()
    else:
        player = connection
    if not player.god:
        return 'Placing god blocks is only allowed in god mode.'
    player.god_build = not player.god_build
    message = ('now placing god blocks.' if player.god_build else
        'no longer placing god blocks.')
    if connection is not player:
        connection.send_chat('%s is %s' % (player.name, message))
    player.send_chat("You're %s" % message)
    connection.protocol.irc_say('* %s is %s' % (player.name, message))

@admin
def fly(connection, player = None):
    if player is not None:
        player = get_player(connection.protocol, player)
    elif connection not in connection.protocol.players:
        raise ValueError()
    else:
        player = connection
    player.fly = not player.fly
    message = 'now flying' if player.fly else 'no longer flying'
    connection.protocol.irc_say('* %s is %s' % (player.name, message))
    if connection is player:
        return "You're %s." % message
    else:
        player.send_chat("You're %s." % message)
        if connection in connection.protocol.players:
            return '%s is %s.' % (player.name, message)

from pyspades.server import kill_action, create_player, position_data
from pyspades.server import orientation_data, input_data
from pyspades.server import set_tool, set_color
from pyspades.common import make_color

@admin
def invisible(connection, player = None):
    if player is not None:
        player = get_player(connection.protocol, player)
    elif connection in connection.protocol.players:
        player = connection
    else:
        raise ValueError()
    player.invisible = not player.invisible
    player.filter_visibility_data = player.invisible
    player.god = player.invisible
    player.god_build = False
    player.killing = not player.invisible
    if player.invisible:
        player.send_chat("You're now invisible.")
        connection.protocol.irc_say('* %s became invisible' % player.name)
        position_data.set((0, 0, 0), player.player_id)
        kill_action.not_fall = True
        kill_action.player1 = kill_action.player2 = player.player_id
        player.protocol.send_contained(position_data, sender = player)
        player.protocol.send_contained(kill_action, sender = player,
            save = True)
    else:
        player.send_chat("You return to visibility.")
        connection.protocol.irc_say('* %s became visible' % player.name)
        pos = player.team.get_random_location()
        x, y, z = pos
        create_player.player_id = player.player_id
        create_player.name = None
        create_player.x = x
        create_player.y = y - 128
        create_player.weapon = player.weapon
        world_object = player.world_object
        position_data.set(world_object.position.get(), player.player_id)
        orientation_data.set(world_object.orientation.get(), player.player_id)
        input_data.up = world_object.up
        input_data.down = world_object.down
        input_data.left = world_object.left
        input_data.right = world_object.right
        input_data.player_id = player.player_id
        input_data.fire = world_object.fire
        input_data.jump = world_object.jump
        input_data.crouch = world_object.crouch
        input_data.aim = world_object.aim
        input_data.player_id = player.player_id
        set_tool.player_id = player.player_id
        set_tool.value = player.tool
        set_color.player_id = player.player_id
        set_color.value = make_color(*player.color)
        player.protocol.send_contained(create_player, sender = player,
            save = True)
        player.protocol.send_contained(position_data, sender = player)
        player.protocol.send_contained(orientation_data, sender = player)
        player.protocol.send_contained(set_tool, sender = player)
        player.protocol.send_contained(set_color, sender = player,
            save = True)
        player.protocol.send_contained(input_data, sender = player)
    if connection is player or connection not in connection.protocol.players:
        return
    if player.invisible:
        return '%s is now invisible' % player.name
    else:
        return '%s is now visible' % player.name

@admin
def ip(connection, value = None):
    if value is None:
        if connection not in connection.protocol.players:
            raise ValueError()
        player = connection
    else:
        player = get_player(connection.protocol, value)
    return 'The IP of %s is %s' % (player.name, player.address[0])

@name('resetgame')
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

from map import Map
from pyspades.load import VXLData

@name('changemap')
@admin
def change_map(connection, value):
    protocol = connection.protocol
    if protocol.rollback_in_progress:
        return 'Rollback in progress.'
    protocol.map_info = Map(value)
    protocol.map = protocol.map_info.data
    protocol.world.map = protocol.map
    protocol.send_chat("The server is changing maps to '%s'!" % value)
    protocol.irc_say("* %s changed map to '%s'" % (connection.name, value))
    for conn in protocol.connections.values():
        conn.disconnect()
    if protocol.rollback_map is not None:
        protocol.rollback_map = protocol.map.copy()
    if hasattr(protocol, 'block_info'):
        # this is very ugly - we need a 'map updated' event
        protocol.block_info = None
    protocol.blue_team.initialize()
    protocol.green_team.initialize()
    protocol.on_game_end(connection)
    protocol.update_entities()
    protocol.update_format()

@name('servername')
@admin
def server_name(connection, *arg):
    name = join_arguments(arg)
    protocol = connection.protocol
    protocol.config['name'] = name
    protocol.update_format()
    if protocol.master_connection is not None:
        protocol.master_connection.disconnect()
    message = "%s changed servername to to '%s'" % (connection.name, name)
    print message
    connection.protocol.irc_say("* " + message)
    if connection in connection.protocol.players:
        return message

@name('master')
@admin
def toggle_master(connection):
    protocol = connection.protocol
    protocol.master = not protocol.master
    if protocol.master_connection is None:
        protocol.set_master()
    else:
        protocol.master_connection.disconnect()
    message = ("toggled master broadcast %s." % ['off', 'on'][
        int(protocol.master)])
    protocol.irc_say("* %s " % connection.name + message)
    return ("You " + message)

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

@admin
def fog(connection, r, g, b):
    r = int(r)
    g = int(g)
    b = int(b)
    connection.protocol.set_fog_color((r, g, b))

def weapon(connection, value):
    player = get_player(connection.protocol, value)
    if player.weapon == SEMI_WEAPON:
        weapon = 'Rifle'
    elif player.weapon == SMG_WEAPON:
        weapon = 'SMG'
    elif player.weapon == SHOTGUN_WEAPON:
        weapon = 'Shotgun'
    else:
        weapon = '(unknown)'
    return '%s has a %s.' % (player.name, weapon)
    
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
    fog,
    ban,
    banip,
    unban,
    undo_ban,
    mute,
    unmute,
    deaf,
    global_chat,
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
    tpsilent,
    go_to,
    move,
    where,
    god,
    god_build,
    fly,
    invisible,
    streak,
    reset_game,
    toggle_master,
    change_map,
    server_name,
    ping,
    weapon
]

commands = {}

for command_func in command_list:
    commands[command_func.func_name] = command_func

rights = {
    'builder' : ['god', 'goto']
}

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
        if hasattr(command_func, 'admin'):
            if (not connection.admin and 
                (connection.rights is None or
                command_func.func_name not in connection.rights)):
                return 'No administrator rights!'
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
