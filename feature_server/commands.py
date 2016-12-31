# Copyright (c) Mathias Kaerlev 2011-2012.

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

import os
import math
from random import choice
from pyspades.constants import *
from pyspades.common import prettify_timespan
from pyspades.server import parse_command
from twisted.internet import reactor

from map import check_rotation

import cfg

class InvalidPlayer(Exception):
    pass

class InvalidSpectator(InvalidPlayer):
    pass

class InvalidTeam(Exception):
    pass

def restrict(func, user_types):
    def new_func(connection, *arg, **kw):
        return func(connection, *arg, **kw)
    new_func.func_name = func.func_name
    new_func.user_types = set(user_types)
    return new_func

def admin(func):
    return restrict(func, ('admin',))

def name(name):
    def dec(func):
        func.func_name = name
        return func
    return dec

def alias(name):
    def dec(func):
        try:
            func.aliases.append(name)
        except AttributeError:
            func.aliases = [name]
        return func
    return dec

def get_player(protocol, value, spectators = True):
    ret = None
    try:
        if value.startswith('#'):
            value = int(value[1:])
            ret = protocol.players[value]
        else:
            players = protocol.players
            try:
                ret = players[value]
            except KeyError:
                value = value.lower()
                for player in players.values():
                    name = player.name.lower()
                    if name == value:
                        return player
                    if name.count(value):
                        ret = player
    except (KeyError, IndexError, ValueError):
        pass
    if ret is None:
        raise InvalidPlayer()
    elif not spectators and ret.world_object is None:
        raise InvalidSpectator()
    return ret

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

def parse_maps(pre_maps):
    maps = []
    for n in pre_maps:
        if n[0]=="#" and len(maps)>0:
            maps[-1] += " "+n
        else:
            maps.append(n)

    return maps, ', '.join(maps)

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

@admin
def hban(connection, value, *arg):
    duration = int(60)
    reason = join_arguments(arg)
    player = get_player(connection.protocol, value)
    player.ban(reason, duration)

@admin
def dban(connection, value, *arg):
    duration = int(1440)
    reason = join_arguments(arg)
    player = get_player(connection.protocol, value)
    player.ban(reason, duration)

@admin
def wban(connection, value, *arg):
    duration = int(10080)
    reason = join_arguments(arg)
    player = get_player(connection.protocol, value)
    player.ban(reason, duration)

@admin
def banip(connection, ip, *arg):
    duration, reason = get_ban_arguments(connection, arg)
    try:
        connection.protocol.add_ban(ip, reason, duration)
    except ValueError:
        return 'Invalid IP address/network'
    reason = ': ' + reason if reason is not None else ''
    duration = duration or None
    if duration is None:
        return 'IP/network %s permabanned%s' % (ip, reason)
    else:
        return 'IP/network %s banned for %s%s' % (ip,
            prettify_timespan(duration * 60), reason)

@admin
def unban(connection, ip):
    try:
        connection.protocol.remove_ban(ip)
        return 'IP unbanned'
    except KeyError:
        return 'IP not found in ban list'

@name('undoban')
@admin
def undo_ban(connection, *arg):
    if len(connection.protocol.bans)>0:
        result = connection.protocol.undo_last_ban()
        return ('Ban for %s undone' % result[0])
    else:
        return 'No bans to undo!'

@admin
def say(connection, *arg):
    value = ' '.join(arg)
    connection.protocol.send_chat(value)
    connection.protocol.irc_say(value)

@admin
def kill(connection, value):
    player = get_player(connection.protocol, value, False)
    player.kill()
    message = '%s killed %s' % (connection.name, player.name)
    connection.protocol.send_chat(message, irc = True)

@admin
def heal(connection, player = None):
    if player is not None:
        player = get_player(connection.protocol, player, False)
        message = '%s was healed by %s' % (player.name, connection.name)
    else:
        if connection not in connection.protocol.players:
            raise ValueError()
        player = connection
        message = '%s was healed' % (connection.name)
    player.refill()
    connection.protocol.send_chat(message, irc = True)

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
            if command.func_name in connection.rights]
        return 'Available commands: %s' % (', '.join(names))

def login(connection, password):
    """
    Login as a user type
    """
    if connection not in connection.protocol.players:
        raise KeyError()
    for user_type, passwords in connection.protocol.passwords.iteritems():
        if password in passwords:
            if user_type in connection.user_types:
                return "You're already logged in as %s" % user_type
            return connection.on_user_login(user_type, True)
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

@name('admin')
def to_admin(connection, *arg):
    protocol = connection.protocol
    message = join_arguments(arg)
    if not message:
        return "Enter a message you want to send, like /admin I'm stuck"
    prefix = '(TO ADMINS)'
    irc_relay = protocol.irc_relay
    if irc_relay:
        if irc_relay.factory.bot and irc_relay.factory.bot.colors:
            prefix = '\x0304' + prefix + '\x0f'
        irc_relay.send(prefix + ' <%s> %s' % (connection.name, message))
    for player in protocol.players.values():
        if player.admin and player is not connection:
            player.send_chat('To ADMINS from %s: %s' %
                (connection.name, message))
    return 'Message sent to admins'

def streak(connection):
    if connection not in connection.protocol.players:
        raise KeyError()
    return ('Your current kill streak is %s. Best is %s kills' %
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
def switch(connection, player = None):
    protocol = connection.protocol
    if player is not None:
        player = get_player(protocol, player)
    elif connection in protocol.players:
        player = connection
    else:
        raise ValueError()
    if player.team.spectator:
        player.send_chat("The switch command can't be used on a spectating player.")
        return
    if player.invisible:
        old_team = player.team
        player.team = player.team.other
        player.on_team_changed(old_team)
        player.spawn(player.world_object.position.get())
        player.send_chat('Switched to %s team' % player.team.name)
        if connection is not player and connection in protocol.players:
            connection.send_chat('Switched %s to %s team' % (player.name,
                player.team.name))
        protocol.irc_say('* %s silently switched teams' % player.name)
    else:
        player.respawn_time = protocol.respawn_time
        player.set_team(player.team.other)
        protocol.send_chat('%s switched teams' % player.name, irc = True)

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
@alias('tb')
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
@alias('tk')
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
        if not connection.admin and not connection.rights.deaf:
            return 'No administrator rights!'
        connection = get_player(connection.protocol, value)
    message = '%s deaf' % ('now' if not connection.deaf else 'no longer')
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

@alias('tp')
@admin
def teleport(connection, player1, player2 = None, silent = False):
    player1 = get_player(connection.protocol, player1)
    if player2 is not None:
        if connection.admin or connection.rights.teleport_other:
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
def unstick(connection, player = None):
    if player is not None:
        player = get_player(connection.protocol, player)
    else:
        player = connection
    connection.protocol.send_chat("%s unstuck %s" %
        (connection.name, player.name), irc = True)
    player.set_location_safe(player.get_location())

@alias('tps')
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
        message = '%s returned to being a mere human' % connection.name
    connection.protocol.send_chat(message, irc = True)

@name('godbuild')
@admin
def god_build(connection, player = None):
    protocol = connection.protocol
    if player is not None:
        player = get_player(protocol, player)
    elif connection in protocol.players:
        player = connection
    else:
        raise ValueError()
    if not player.god:
        return 'Placing god blocks is only allowed in god mode'
    player.god_build = not player.god_build

    message = ('now placing god blocks' if player.god_build else
        'no longer placing god blocks')
    player.send_chat("You're %s" % message)
    if connection is not player and connection in protocol.players:
        connection.send_chat('%s is %s' % (player.name, message))
    protocol.irc_say('* %s is %s' % (player.name, message))

@admin
def fly(connection, player = None):
    protocol = connection.protocol
    if player is not None:
        player = get_player(protocol, player)
    elif connection in protocol.players:
        player = connection
    else:
        raise ValueError()
    player.fly = not player.fly

    message = 'now flying' if player.fly else 'no longer flying'
    player.send_chat("You're %s" % message)
    if connection is not player and connection in protocol.players:
        connection.send_chat('%s is %s' % (player.name, message))
    protocol.irc_say('* %s is %s' % (player.name, message))

from pyspades.contained import KillAction
from pyspades.server import create_player, set_tool, set_color, input_data, weapon_input
from pyspades.common import make_color

@alias('invis')
@alias('inv')
@admin
def invisible(connection, player = None):
    protocol = connection.protocol
    if player is not None:
        player = get_player(protocol, player)
    elif connection in protocol.players:
        player = connection
    else:
        raise ValueError()
    player.invisible = not player.invisible
    player.filter_visibility_data = player.invisible
    player.god = player.invisible
    player.god_build = False
    player.killing = not player.invisible
    if player.invisible:
        player.send_chat("You're now invisible")
        protocol.irc_say('* %s became invisible' % player.name)
        kill_action = KillAction()
        kill_action.kill_type = choice([GRENADE_KILL, FALL_KILL])
        kill_action.player_id = kill_action.killer_id = player.player_id
        reactor.callLater(1.0 / NETWORK_FPS, protocol.send_contained,
            kill_action, sender = player)
    else:
        player.send_chat("You return to visibility")
        protocol.irc_say('* %s became visible' % player.name)
        x, y, z = player.world_object.position.get()
        create_player.player_id = player.player_id
        create_player.name = player.name
        create_player.x = x
        create_player.y = y
        create_player.z = z
        create_player.weapon = player.weapon
        create_player.team = player.team.id
        world_object = player.world_object
        input_data.player_id = player.player_id
        input_data.up = world_object.up
        input_data.down = world_object.down
        input_data.left = world_object.left
        input_data.right = world_object.right
        input_data.jump = world_object.jump
        input_data.crouch = world_object.crouch
        input_data.sneak = world_object.sneak
        input_data.sprint = world_object.sprint
        set_tool.player_id = player.player_id
        set_tool.value = player.tool
        set_color.player_id = player.player_id
        set_color.value = make_color(*player.color)
        weapon_input.primary = world_object.primary_fire
        weapon_input.secondary = world_object.secondary_fire
        protocol.send_contained(create_player, sender = player, save = True)
        protocol.send_contained(set_tool, sender = player)
        protocol.send_contained(set_color, sender = player, save = True)
        protocol.send_contained(input_data, sender = player)
        protocol.send_contained(weapon_input, sender = player)
    if connection is not player and connection in protocol.players:
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

@name('whowas')
@admin
def who_was(connection, value):
    value = value.lower()
    ret = None
    exact_match = False
    for name, ip in connection.protocol.player_memory:
        name_lower = name.lower()
        if name_lower == value:
            ret = (name, ip)
            exact_match = True
        elif not exact_match and name_lower.count(value):
            ret = (name, ip)
    if ret is None:
        raise InvalidPlayer()
    return "%s's most recent IP was %s" % ret

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
    connection.protocol.on_game_end()
    connection.protocol.send_chat('Game has been reset by %s' % connection.name,
        irc = True)

from map import Map
import itertools

@name('map')
@admin
def change_planned_map(connection, *pre_maps):
    name = connection.name
    protocol = connection.protocol

    # parse seed numbering
    maps, map_list = parse_maps(pre_maps)
    if not maps:
        return 'Invalid map name'

    map = maps[0]
    protocol.planned_map = check_rotation([map])[0]
    protocol.send_chat('%s changed next map to %s' % (name, map), irc = True)

@name('rotation')
@admin
def change_rotation(connection, *pre_maps):
    name = connection.name
    protocol = connection.protocol

    maps, map_list = parse_maps(pre_maps)

    if len(maps) == 0:
        return 'Usage: /rotation <map1> <map2> <map3>...'
    ret = protocol.set_map_rotation(maps, False)
    if not ret:
        return 'Invalid map in map rotation (%s)' % ret.map
    protocol.send_chat("%s changed map rotation to %s." %
                            (name, map_list), irc=True)

@name('rotationadd')
@admin
def rotation_add(connection, *pre_maps):
    name = connection.name
    protocol = connection.protocol

    new_maps, map_list = parse_maps(pre_maps)

    maps = connection.protocol.get_map_rotation()
    map_list = ", ".join(maps) + map_list
    maps.extend(new_maps)

    ret = protocol.set_map_rotation(maps, False)
    if not ret:
        return 'Invalid map in map rotation (%s)' % ret.map
    protocol.send_chat("%s added %s to map rotation." %
                            (name, " ".join(pre_maps)), irc=True)

@name('showrotation')
def show_rotation(connection):
    return ", ".join(connection.protocol.get_map_rotation())

@name('revertrotation')
@admin
def revert_rotation(connection):
    protocol = connection.protocol
    maps = protocol.config['maps']
    protocol.set_map_rotation(maps, False)
    protocol.irc_say("* %s reverted map rotation to %s" % (name, maps))

def mapname(connection):
    return 'Current map: ' + connection.protocol.map_info.name

@admin
def advance(connection):
    connection.protocol.advance_rotation('Map advance forced.')

@name('timelimit')
@admin
def set_time_limit(connection, value):
    value = float(value)
    protocol = connection.protocol
    protocol.set_time_limit(value)
    protocol.send_chat('Time limit set to %s' % value, irc = True)

@name('time')
def get_time_limit(connection):
    advance_call = connection.protocol.advance_call
    if advance_call is None:
        return 'No time limit set'
    left = int(math.ceil((advance_call.getTime() - reactor.seconds()) / 60.0))
    return 'There are %s minutes left' % left

@name('servername')
@admin
def server_name(connection, *arg):
    name = join_arguments(arg)
    protocol = connection.protocol
    protocol.config['name'] = name
    protocol.update_format()
    message = "%s changed servername to to '%s'" % (connection.name, name)
    print message
    connection.protocol.irc_say("* " + message)
    if connection in connection.protocol.players:
        return message

@name('master')
@admin
def toggle_master(connection):
    protocol = connection.protocol
    protocol.set_master_state(not protocol.master)
    message = ("toggled master broadcast %s" % ['OFF', 'ON'][
        int(protocol.master)])
    protocol.irc_say("* %s " % connection.name + message)
    if connection in connection.protocol.players:
        return ("You " + message)

def ping(connection, value = None):
    if value is None:
        if connection not in connection.protocol.players:
            raise ValueError()
        player = connection
    else:
        player = get_player(connection.protocol, value)
    ping = player.latency
    if value is None:
        return ('Your ping is %s ms. Lower ping is better!' % ping)
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
    return "Nobody in your team has the enemy intel"

def version(connection):
    return 'Server version is "%s"' % connection.protocol.server_version

@name('server')
def server_info(connection):
    protocol = connection.protocol
    msg = 'You are playing on "%s"' % protocol.name
    if protocol.identifier is not None:
        msg += ' at %s' % protocol.identifier
    return msg

def scripts(connection):
    scripts = connection.protocol.config.get('scripts', [])
    return 'Scripts enabled: %s' % (', '.join(scripts))

@admin
def fog(connection, r, g, b):
    r = int(r)
    g = int(g)
    b = int(b)
    connection.protocol.set_fog_color((r, g, b))

def weapon(connection, value):
    player = get_player(connection.protocol, value)
    if player.weapon_object is None:
        name = '(unknown)'
    else:
        name = player.weapon_object.name
    return '%s has a %s' % (player.name, name)

command_list = [
    help,
    pm,
    to_admin,
    login,
    kick,
    intel,
    ip,
    who_was,
    fog,
    ban,
    hban,
    dban,
    wban,
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
    tpsilent,
    go_to,
    move,
    unstick,
    where,
    god,
    god_build,
    fly,
    invisible,
    streak,
    reset_game,
    toggle_master,
    change_planned_map,
    change_rotation,
    revert_rotation,
    show_rotation,
    rotation_add,
    advance,
    set_time_limit,
    get_time_limit,
    server_name,
    ping,
    version,
    server_info,
    scripts,
    weapon,
    mapname
]

commands = {}
aliases = {}
rights = {}

def add(func, name = None):
    """
    Function to add a command from scripts
    """
    if name is None:
        name = func.func_name
    name = name.lower()
    user_types = getattr(func, 'user_types', None)
    if user_types is not None:
        for user_type in user_types:
            if user_type in rights:
                rights[user_type].add(name)
            else:
                rights[user_type] = set([name])
    commands[name] = func
    try:
        for alias in func.aliases:
            aliases[alias.lower()] = name
    except AttributeError:
        pass

for command_func in command_list:
    add(command_func)

# optional commands
try:
    import pygeoip
    database = pygeoip.GeoIP(os.path.join(cfg.config_dir, 'data/GeoLiteCity.dat'))
    
    @name('from')
    def where_from(connection, value = None):
        if value is None:
            if connection not in connection.protocol.players:
                raise ValueError()
            player = connection
        else:
            player = get_player(connection.protocol, value)
        record = database.record_by_addr(player.address[0])
        if record is None:
            return 'Player location could not be determined.'
        items = []
        for entry in ('country_name', 'city', 'region_name'):
            # sometimes, the record entries are numbers or nonexistent
            try:
                value = record[entry]
                int(value) # if this raises a ValueError, it's not a number
                continue
            except KeyError:
                continue
            except ValueError:
                pass
            if type(value) is not type(''):
                continue
            items.append(value)
        return '%s is from %s' % (player.name, ', '.join(items))
    add(where_from)
except ImportError:
    print "('from' command disabled - missing pygeoip)"
except (IOError, OSError):
    print "('from' command disabled - missing data/GeoLiteCity.dat)"

def handle_command(connection, command, parameters):
    command = command.lower()
    try:
        command = aliases[command]
    except KeyError:
        pass
    try:
        command_func = commands[command]
    except KeyError:
        return # 'Invalid command'
    try:
        if (hasattr(command_func, 'user_types') and
            command_func.func_name not in connection.rights):
                return "You can't use this command"
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

def debug_handle_command(connection, command, parameters):
    # use this when regular handle_command eats errors
    if connection in connection.protocol.players:
        connection.send_chat("Commands are in DEBUG mode")
    command = command.lower()
    try:
        command = aliases[command]
    except KeyError:
        pass
    try:
        command_func = commands[command]
    except KeyError:
        return # 'Invalid command'
    if (hasattr(command_func, 'user_types') and
        command_func.func_name not in connection.rights):
            return "You can't use this command"
    return command_func(connection, *parameters)

# handle_command = debug_handle_command

def handle_input(connection, input):
    # for IRC and console
    return handle_command(connection, *parse_command(input))
