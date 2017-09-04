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

# pylint: disable=too-many-lines
# pylint: disable=wildcard-import,unused-wildcard-import

from __future__ import print_function, unicode_literals

import traceback

if __name__ == 'commands':
    # this disgusting hack allows this to be imported both as "commands" and
    # piqueserver.commands
    from piqueserver.commands import *
else:

    import os
    import math
    import inspect
    from random import choice
    import warnings
    from collections import namedtuple
    import textwrap

    from twisted.internet import reactor

    from pyspades.contained import KillAction, InputData, SetColor, WeaponInput
    from pyspades.player import create_player, set_tool, parse_command
    from pyspades.constants import (GRENADE_KILL, FALL_KILL, NETWORK_FPS)
    from pyspades.common import (
        prettify_timespan, coordinates, to_coordinates,
        make_color)
    from piqueserver.map import check_rotation, MapNotFound
    from piqueserver import cfg

    # aparently, we need to send packets in this file. For now, I give in.
    kill_action = KillAction()
    input_data = InputData()
    set_color = SetColor()
    weapon_input = WeaponInput()

    _commands = {}
    _alias_map = {}
    _rights = {}

    class CommandError(Exception):
        pass

    def command(name=None, *aliases):
        """
        Register a new command.

        The command will be accessible as `/function_name` unless a name or alias
        is specified.

        >>> @command()
        ... def some_command(x):
        ...     pass

        Optional mames and aliases:

        >>> @command("name", "alias1", "alias2")
        ... def some_command(x):
        ...     pass
        """
        def decorator(function):
            function.user_types = set()

            # in py2 you can not modify variables in outer closures, so we need
            # to assign into a new variable
            if name is None:
                func_name = function.__name__
            else:
                func_name = name

            function.command_name = func_name

            _commands[func_name] = function

            if aliases:
                function.aliases = []

                for alias in aliases:
                    _alias_map[alias] = func_name

            return function
        return decorator

    def add(func):
        """
        Function to add a command from scripts. Deprecated
        """
        warnings.warn(
            '@add is deprecated, use @command()',
            DeprecationWarning)
        command()(func)

    def name(name):
        """
        Give the command a new name. Deprecated
        """
        warnings.warn(
            '@name is deprecated, use @command("name")',
            DeprecationWarning)
        def dec(func):
            func.__name__ = name
            return func
        return dec

    def alias(name):
        """
        add a new alias to a command. Deprecated
        """
        warnings.warn(
            '@alias is deprecated, use @command("name", "alias1", "alias2")',
            DeprecationWarning)
        def dec(func):
            try:
                func.aliases.append(name)
            except AttributeError:
                func.aliases = [name]
            return func
        return dec

    def restrict(*user_types):
        """
        restrict the command to only be used by a specific type of user

        >>> @restrict("admin", "guard")
        ... @command()
        ... def some_command(x):
        ...     pass
        """
        def decorator(function):
            function.user_types = set(*user_types)
            return function
        return decorator

    def has_permission(f, connection):
        print(f.command_name, "in", connection.rights)

        if not f.user_types:
            return True
        elif f.command_name in connection.rights:
            return True
        elif connection.admin:
            return True
        else:
            return False

    CommandHelp = namedtuple("CommandHelp", ["description", "usage", "info"])
    def get_command_help(command_func):
        doc = command_func.__doc__
        if not doc:
            return CommandHelp("", "", "")

        doc = textwrap.dedent(doc).strip()

        lines = doc.split("\n")

        # Yes, this is disgusting. I wish I could think of a better way of
        # doing it

        count = 0
        desc = ""
        usage = ""
        info = ""

        for line in lines:
            line = line.strip()
            if not line:
                continue
            if count == 0:
                desc = line
            elif count == 1:
                usage = line
            elif count == 2:
                info = line

            count += 1

        return CommandHelp(desc, usage, info)

    def format_command_error(command_func, message, exception=None):
        """format a help message for a given command"""
        command_help = get_command_help(command_func)

        if command_help.usage:
            return "{}\nUsage: {}".format(message, command_help.usage)
        else:
            return message

    # it might seem unecesary to reimplement half of the dict data type for
    # _rights, but previously this attribute was accessed and modified from
    # various places and that made things more confusing than the needed to be

    def add_rights(user_type, command_name):
        """
        Give the user type a new right

        >>> add_rights("knights", "say_ni")
        """
        _rights.setdefault(user_type, []).append(command_name)

    def get_rights(user_type):
        """
        Get a list of rights a specific user type has.

        >>> add_rights("knights", "say_ni")
        >>> get_rights("knights")
        ["say_ni"]
        >>> get_rights("arthur")
        []
        """
        r =  _rights.get(user_type, [])
        return r

    def update_rights(rights):
        """
        Update the rights of all users according to the input dictionary. This
        is currently only here for when the config needs to be reloaded.

        >>> update_rights({"knights": ["say_ni"]})
        >>> get_rights("knights")
        ["say_ni"]
        """
        _rights.update(rights)

    def admin(func):
        """
        Shorthand for @restrict("admin"). Mainly exists for backwards
        compability with pyspades scripts.

        >>> @admin
        ... @command()
        ... def some_command(x):
        ...     pass
        """
        return restrict('admin')(func)

    # TODO: all of these utility functions should be seperated from the actual
    # implementation of the commands

    def get_player(protocol, value, spectators=True):
        """
        Get a player connection object by name or ID.

        IDs are formatted as: "#12"

        If no player with the specified name is found, it will try to find a
        player who's name contains the string
        """
        player_obj = None
        try:
            if value.startswith('#'):
                value = int(value[1:])
                player_obj = protocol.players[value]
            else:
                players = protocol.players
                try:
                    player_obj = players[value]
                except KeyError:
                    value = value.lower()
                    matches = []
                    for player in players.values():
                        name = player.name.lower()
                        if name == value:
                            # if the playername matches, we want to return directly, otherwise
                            # you would not be able to kick players who's name is a subset of
                            # another players name
                            return player
                        if name.count(value):
                            matches.append(player)

                    if len(matches) > 1:
                        # more than one player matched
                        raise CommandError("Ambiguous player")
                    elif len(matches) == 1:
                        player_obj = matches[0]
                    else:
                        # no Players were found
                        player_obj = None
        except (KeyError, IndexError, ValueError):
            pass
        if player_obj is None:
            raise CommandError("Invalid Player")
        elif not spectators and player_obj.world_object is None:
            raise CommandError("Invalid Spectator")
        return player_obj

    def get_team(connection, value):
        value = value.lower()
        if value == 'blue':
            return connection.protocol.blue_team
        elif value == 'green':
            return connection.protocol.green_team
        elif value == 'spectator':
            return connection.protocol.spectator_team
        raise CommandError("Invalid Team")

    def join_arguments(arg, default=None):
        if not arg:
            return default
        return ' '.join(arg)

    def parse_maps(pre_maps):
        maps = []
        for n in pre_maps:
            if n[0] == "#" and len(maps) > 0:
                maps[-1] += " " + n
            else:
                maps.append(n)

        return maps, ', '.join(maps)

    def get_truthy(value):
        value = value.lower()

        if value in ("yes", "y", "on", 1):
            return True
        elif value in ("no", "n", "off", 0):
            return False
        else:
            return None

    ## Actual commands start here

    @admin
    @command()
    def kick(connection, value, *arg):
        """
        kick a player
        /kick <player>
        Player is the #ID of the player, or a unique part of their name
        """
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
            if len(arg) > 0 and arg[0] == "perma":
                arg = arg[1:]
            else:
                duration = connection.protocol.default_ban_time
        reason = join_arguments(arg)
        return duration, reason

    @admin
    @command()
    def ban(connection, value, *arg):
        """
        Ban a player
        /ban <player> [duration] [reason]
        """
        duration, reason = get_ban_arguments(connection, arg)
        player = get_player(connection.protocol, value)
        player.ban(reason, duration)

    @admin
    @command()
    def hban(connection, value, *arg):
        """
        Ban a player for an hour
        /hban <player> [reason]
        """
        duration = 60
        reason = join_arguments(arg)
        player = get_player(connection.protocol, value)
        player.ban(reason, duration)

    @admin
    @command()
    def dban(connection, value, *arg):
        """
        Ban a player for an hour
        /dban <player> [reason]
        """
        duration = 1440
        reason = join_arguments(arg)
        player = get_player(connection.protocol, value)
        player.ban(reason, duration)

    @admin
    @command()
    def wban(connection, value, *arg):
        """
        Ban a player for a week
        /wban <player> [reason]
        """
        duration = 10080
        reason = join_arguments(arg)
        player = get_player(connection.protocol, value)
        player.ban(reason, duration)

    @admin
    @command()
    def pban(connection, value, *arg):
        """
        Ban a player permanently
        /pban <player> [reason]
        """
        duration = 0
        reason = join_arguments(arg)
        player = get_player(connection.protocol, value)
        player.ban(reason, duration)

    @admin
    @command()
    def banip(connection, ip, *arg):
        """
        Ban an ip
        /banip <ip> [reason]
        """
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
            return 'IP/network %s banned for %s%s' % (
                ip, prettify_timespan(duration * 60), reason)

    @admin
    @command()
    def unban(connection, ip):
        """
        Unban an ip
        /unban <ip>
        """
        try:
            connection.protocol.remove_ban(ip)
            return 'IP unbanned'
        except KeyError:
            return 'IP not found in ban list'

    @admin
    @command('undoban')
    def undo_ban(connection, *arg):
        """
        Undo last ban
        /undoban
        """
        if len(connection.protocol.bans) > 0:
            result = connection.protocol.undo_last_ban()
            return 'Ban for %s undone' % result[0]
        else:
            return 'No bans to undo!'

    @admin
    @command()
    def say(connection, *arg):
        """
        Say something in chat as server message
        /say <text>
        """
        value = ' '.join(arg)
        connection.protocol.send_chat(value)
        connection.protocol.irc_say(value)

    @command()
    def kill(connection, value=None):
        """
        Kill a player
        /kill [target]
        """
        if value is None:
            player = connection
        else:
            if not connection.rights.kill and not connection.admin:
                return "You can't use this command"
            player = get_player(connection.protocol, value, False)
        player.kill()
        if connection is not player:
            message = '%s killed %s' % (connection.name, player.name)
            connection.protocol.send_chat(message, irc=True)

    @admin
    @command()
    def heal(connection, player=None):
        """
        Refill an heal a player
        /heal [target]
        """
        if player is not None:
            player = get_player(connection.protocol, player, False)
            message = '%s was healed by %s' % (player.name, connection.name)
        else:
            if connection not in connection.protocol.players:
                raise ValueError()
            player = connection
            message = '%s was healed' % (connection.name)
        player.refill()
        connection.protocol.send_chat(message, irc=True)

    @command()
    def rules(connection):
        """
        Show the rules
        /rules
        """
        if connection not in connection.protocol.players:
            raise KeyError()
        lines = connection.protocol.rules
        if lines is None:
            return
        connection.send_lines(lines)

    @command("help")
    def help_command(connection):
        """
        Print the help Message
        /help
        """
        if connection.protocol.help is not None and not connection.admin:
            connection.send_lines(connection.protocol.help)
        else:

            names = [command.command_name for command in _commands.values()
                     if has_permission(command, connection)]

            return 'Available commands: %s' % (', '.join(names))

    @command()
    def login(connection, password):
        """
        Login as a user type
        /login <password>
        """
        if connection not in connection.protocol.players:
            raise KeyError()
        for user_type, passwords in connection.protocol.passwords.items():
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

    @command()
    def pm(connection, value, *arg):
        """
        Send a player a private message
        /pm <player> <message>
        """
        player = get_player(connection.protocol, value)
        message = join_arguments(arg)
        player.send_chat('PM from %s: %s' % (connection.name, message))
        return 'PM sent to %s' % player.name

    @command('admin')
    def to_admin(connection, *arg):
        """
        Send a notice to the admins
        /admin <message>
        """
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

    @command()
    def streak(connection):
        """
        View your killstreak
        /streak
        """
        if connection not in connection.protocol.players:
            raise KeyError()
        return ('Your current kill streak is %s. Best is %s kills' %
                (connection.streak, connection.best_streak))

    @admin
    @command()
    def lock(connection, value):
        """
        Lock a team
        /lock <blue|green|spectator>
        """
        team = get_team(connection, value)
        team.locked = True
        connection.protocol.send_chat('%s team is now locked' % team.name)
        connection.protocol.irc_say('* %s locked %s team' % (connection.name,
                                                             team.name))

    @admin
    @command()
    def unlock(connection, value):
        """
        Unlock a team
        /unlock <blue|green|spectator>
        """
        team = get_team(connection, value)
        team.locked = False
        connection.protocol.send_chat('%s team is now unlocked' % team.name)
        connection.protocol.irc_say('* %s unlocked %s team' % (connection.name,
                                                               team.name))

    @admin
    @command()
    def switch(connection, player=None, team=None):
        """
        switch a players team
        /switch [player]
        """
        protocol = connection.protocol
        if player is not None:
            player = get_player(protocol, player)
        elif connection in protocol.players:
            player = connection
        else:
            raise ValueError()
        if player.team.spectator:
            player.send_chat(
                "The switch command can't be used on a spectating player.")
            return
        if team is None:
            new_team = player.team.other
        else:
            new_team = get_team(connection, team)
        if player.invisible:
            old_team = player.team
            player.team = new_team
            player.on_team_changed(old_team)
            player.spawn(player.world_object.position.get())
            player.send_chat('Switched to %s team' % player.team.name)
            if connection is not player and connection in protocol.players:
                connection.send_chat('Switched %s to %s team' % (player.name,
                                                                 player.team.name))
            protocol.irc_say('* %s silently switched teams' % player.name)
        else:
            player.respawn_time = protocol.respawn_time
            player.set_team(new_team)
            protocol.send_chat('%s switched teams' % player.name, irc=True)

    @admin
    @command('setbalance')
    def set_balance(connection, value):
        """
        Turn automatic balancing on or off
        /setbalance <on|off>
        """
        should_balance = get_truthy(value)
        if should_balance is None:
            raise CommandError()

        protocol = connection.protocol
        protocol.balanced_teams = should_balance

        if should_balance:
            protocol.send_chat('now balancing teams')
            connection.protocol.irc_say(
                '* %s turned on balanced teams' % connection.name)
        else:
            protocol.send_chat('now no longer balancing teams')
            connection.protocol.irc_say(
                '* %s turned off balanced teams' % connection.name)

    @admin
    @command('togglebuild', 'tb')
    def toggle_build(connection, player=None):
        """
        Toggle building
        /togglebuild [player]
        """
        if player is not None:
            player = get_player(connection.protocol, player)
            value = not player.building
            player.building = value
            msg = '%s can build again' if value else '%s is disabled from building'
            connection.protocol.send_chat(msg % player.name)
            connection.protocol.irc_say('* %s %s building for %s' %
                                        (connection.name,
                                         ['disabled', 'enabled'][int(value)],
                                         player.name))
        else:
            value = not connection.protocol.building
            connection.protocol.building = value
            on_off = ['OFF', 'ON'][int(value)]
            connection.protocol.send_chat('Building has been toggled %s!' % on_off)
            connection.protocol.irc_say(
                '* %s toggled building %s' % (connection.name,
                                              on_off))

    @admin
    @command('togglekill', 'tk')
    def toggle_kill(connection, player=None):
        """
        Toggle killing
        /togglekill [player]
        """
        if player is not None:
            player = get_player(connection.protocol, player)
            value = not player.killing
            player.killing = value
            msg = '%s can kill again' if value else '%s is disabled from killing'
            connection.protocol.send_chat(msg % player.name)
            connection.protocol.irc_say('* %s %s killing for %s' %
                                        (connection.name,
                                         ['disabled', 'enabled'][int(value)], player.name))
        else:
            value = not connection.protocol.killing
            connection.protocol.killing = value
            on_off = ['OFF', 'ON'][int(value)]
            connection.protocol.send_chat('Killing has been toggled %s!' % on_off)
            connection.protocol.irc_say(
                '* %s toggled killing %s' % (connection.name,
                                             on_off))

    @admin
    @command('toggleteamkill', 'ttk')
    def toggle_teamkill(connection):
        """
        Toggle teamkilling
        /toggleteamkill
        """
        value = not connection.protocol.friendly_fire
        connection.protocol.friendly_fire = value
        on_off = ['OFF', 'ON'][int(value)]
        connection.protocol.send_chat(
            'Friendly fire has been toggled %s!' % on_off)
        connection.protocol.irc_say('* %s toggled friendly fire %s' % (
            connection.name, on_off))

    @admin
    @command()
    def mute(connection, value):
        """
        Mute a player
        /mute <player>
        """
        player = get_player(connection.protocol, value)
        if player.mute:
            return '%s is already muted' % player.name
        player.mute = True
        message = '%s has been muted by %s' % (player.name, connection.name)
        connection.protocol.send_chat(message, irc=True)

    @admin
    @command()
    def unmute(connection, value):
        """
        Unmute a player
        /unmute <player>
        """
        player = get_player(connection.protocol, value)
        if not player.mute:
            return '%s is not muted' % player.name
        player.mute = False
        message = '%s has been unmuted by %s' % (player.name, connection.name)
        connection.protocol.send_chat(message, irc=True)

    @command()
    def deaf(connection, value=None):
        """
        No longer recieve chat messages
        /deaf [player]
        """
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

    @admin
    @command('globalchat')
    def global_chat(connection, value=None):
        """
        Enable or disable global chat
        /globalchat [on|off]
        """
        enabled = get_truthy(value)
        if enabled is True:
            connection.protocol.global_chat = True
        elif enabled is False:
            connection.protocol.global_chat = False
        else:
            connection.protocol.global_chat = not connection.protocol.global_chat

        connection.protocol.send_chat(
            'Global chat %s' % (
                'enabled' if connection.protocol.global_chat else 'disabled'),
            irc=True)

    @admin
    @command('teleport', 'tp')
    def teleport(connection, player1, player2=None, silent=False):
        """
        Teleport a player to another player
        /teleport [player] <target player>
        """
        # TODO: refactor this
        player1 = get_player(connection.protocol, player1)
        if player2 is not None:
            if connection.admin or connection.rights.teleport_other:
                player, target = player1, get_player(
                    connection.protocol, player2)
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
            message = '%s ' + \
                ('silently ' if silent else '') + 'teleported to %s'
            message = message % (player.name, target.name)
        x, y, z = target.get_location()
        player.set_location(((x - 0.5), (y - 0.5), (z + 0.5)))
        if silent:
            connection.protocol.irc_say('* ' + message)
        else:
            connection.protocol.send_chat(message, irc=True)

    @admin
    @command('tpsilent', 'tps')
    def tpsilent(connection, player1, player2=None):
        """
        Silently teleport a player to another player
        /tpsilent [player] <target player>
        """
        teleport(connection, player1, player2, silent=True)

    @admin
    @command()
    def unstick(connection, player=None):
        """
        Unstick yourself or another player
        /unstick [player]
        """
        if player is not None:
            player = get_player(connection.protocol, player)
        else:
            player = connection
        connection.protocol.send_chat("%s unstuck %s" %
                                      (connection.name, player.name), irc=True)
        player.set_location_safe(player.get_location())

    @admin
    @command('goto')
    def go_to(connection, value):
        """
        Go to a specified sector
        /goto <sector>
        """
        if connection not in connection.protocol.players:
            raise KeyError()
        move(connection, connection.name, value, silent=connection.invisible)

    @admin
    @command('gotos')
    def go_to_silent(connection, value):
        """
        Silently go to a specified sector
        /gotos <sector>
        """
        if connection not in connection.protocol.players:
            raise KeyError()
        move(connection, connection.name, value, True)

    @admin
    @command()
    def move(connection, player, value, silent=False):
        """
        Go to a specified sector
        /move <player> <sector>
        """
        player = get_player(connection.protocol, player)
        x, y = coordinates(value)
        x += 32
        y += 32
        player.set_location(
            (x, y, connection.protocol.map.get_height(x, y) - 2))
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
            connection.protocol.send_chat(message, irc=True)

    @admin
    @command()
    def where(connection, player=None):
        """
        Find the location of a player
        /where [player]
        """
        if player is not None:
            connection = get_player(connection.protocol, player)
        elif connection not in connection.protocol.players:
            raise ValueError()
        x, y, z = connection.get_location()
        return '%s is in %s (%s, %s, %s)' % (connection.name,
                                             to_coordinates(x, y), int(x), int(y), int(z))

    @admin
    @command('godsilent', 'gods')
    def godsilent(connection, player=None):
        """
        Silently go into god mode
        /godsilent [player]
        """
        if player is not None:
            connection = get_player(connection.protocol, player)
        elif connection not in connection.protocol.players:
            raise ValueError()
        connection.god = not connection.god
        if connection.protocol.set_god_build:
            connection.god_build = connection.god
        else:
            connection.god_build = False
        #TODO: Return different message if other player is put into god mode
        return 'You have entered god mode.'

    @admin
    @command()
    def god(connection, player=None):
        """
        Go into god mode
        /god [player]
        """
        godsilent(connection, player)
        if connection.god:
            message = '%s entered GOD MODE!' % connection.name
        else:
            message = '%s returned to being a mere human' % connection.name
        connection.protocol.send_chat(message, irc=True)

    @admin
    @command('godbuild')
    def god_build(connection, player=None):
        """
        Enable placing god blocks
        /godbuild [player]
        """
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
    @command()
    def fly(connection, player=None):
        """
        Enable flight
        /fly [player]
        """
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

    @admin
    @command('invisible', 'invis', 'inv')
    def invisible(connection, player=None):
        """
        Turn invisible
        /invisible [player]
        """
        protocol = connection.protocol
        if player is not None:
            player = get_player(protocol, player)
        elif connection in protocol.players:
            player = connection
        else:
            raise ValueError()
        # TODO: move this logic to a more suitable place
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
                              kill_action, sender=player)
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
            protocol.send_contained(create_player, sender=player, save=True)
            protocol.send_contained(set_tool, sender=player)
            protocol.send_contained(set_color, sender=player, save=True)
            protocol.send_contained(input_data, sender=player)
            protocol.send_contained(weapon_input, sender=player)
        if connection is not player and connection in protocol.players:
            if player.invisible:
                return '%s is now invisible' % player.name
            else:
                return '%s is now visible' % player.name

    @admin
    @command()
    def ip(connection, value=None):
        """
        Get the IP of a user
        /ip [player]
        """
        if value is None:
            if connection not in connection.protocol.players:
                raise ValueError()
            player = connection
        else:
            player = get_player(connection.protocol, value)
        return 'The IP of %s is %s' % (player.name, player.address[0])

    @admin
    @command("whowas")
    def who_was(connection, value):
        """
        Get the IP of a user who has left
        /whowas <player>
        """
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
            raise CommandError("Invalid Player")
        return "%s's most recent IP was %s" % ret

    @admin
    @command("resetgame")
    def reset_game(connection):
        """
        reset the game
        /resetgame
        """
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
        connection.protocol.send_chat(
            'Game has been reset by %s' % connection.name,
            irc=True)

    @admin
    @command('map')
    def change_planned_map(connection, *pre_maps):
        """
        set the next map
        /map <mapname>
        """
        name = connection.name
        protocol = connection.protocol

        # parse seed numbering
        maps, _map_list = parse_maps(pre_maps)
        if not maps:
            return 'Invalid map name'

        planned_map = maps[0]
        try:
            protocol.planned_map = check_rotation([planned_map])[0]
            protocol.send_chat('%s changed next map to %s' %
                               (name, planned_map), irc=True)
        except MapNotFound:
            return 'Map %s not found' % (maps[0])

    @admin
    @command('rotation')
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

    @admin
    @command('rotationadd')
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

    @command('showrotation')
    def show_rotation(connection):
        return ", ".join(connection.protocol.get_map_rotation())

    @admin
    @command('revertrotation')
    def revert_rotation(connection):
        protocol = connection.protocol
        maps = protocol.config['maps']
        protocol.set_map_rotation(maps, False)
        protocol.irc_say("* %s reverted map rotation to %s" % (name, maps))

    @command()
    def mapname(connection):
        return 'Current map: ' + connection.protocol.map_info.name

    @admin
    @command('advancemap')
    def advance(connection):
        connection.protocol.advance_rotation('Map advance forced.')

    @admin
    @command('timelimit')
    def set_time_limit(connection, value):
        value = float(value)
        protocol = connection.protocol
        protocol.set_time_limit(value)
        protocol.send_chat('Time limit set to %s' % value, irc=True)

    @command('time')
    def get_time_limit(connection):
        advance_call = connection.protocol.advance_call
        if advance_call is None:
            return 'No time limit set'
        left = int(
            math.ceil((advance_call.getTime() - reactor.seconds()) / 60.0))
        return 'There are %s minutes left' % left

    @admin
    @command('servername')
    def server_name(connection, *arg):
        name = join_arguments(arg)
        protocol = connection.protocol
        protocol.config['name'] = name
        protocol.update_format()
        message = "%s changed servername to to '%s'" % (connection.name, name)
        print(message)
        connection.protocol.irc_say("* " + message)
        if connection in connection.protocol.players:
            return message

    @admin
    @command('togglemaster', 'master')
    def toggle_master(connection):
        protocol = connection.protocol
        protocol.set_master_state(not protocol.master)
        message = ("toggled master broadcast %s" % ['OFF', 'ON'][
            int(protocol.master)])
        protocol.irc_say("* %s " % connection.name + message)
        if connection in connection.protocol.players:
            return "You " + message

    @command()
    def ping(connection, value=None):
        if value is None:
            if connection not in connection.protocol.players:
                raise ValueError()
            player = connection
        else:
            player = get_player(connection.protocol, value)
        ping = player.latency
        if value is None:
            return 'Your ping is %s ms. Lower ping is better!' % ping
        return "%s's ping is %s ms" % (player.name, ping)

    @command()
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

    @command()
    def version(connection):
        return 'Server version is "%s"' % connection.protocol.server_version

    @command('server')
    def server_info(connection):
        protocol = connection.protocol
        msg = 'You are playing on "%s"' % protocol.name
        if protocol.identifier is not None:
            msg += ' at %s' % protocol.identifier
        return msg

    @command()
    def scripts(connection):
        scripts = connection.protocol.config.get('scripts', [])
        return 'Scripts enabled: %s' % (', '.join(scripts))

    @admin
    @command()
    def fog(connection, r, g, b):
        r = int(r)
        g = int(g)
        b = int(b)
        connection.protocol.set_fog_color((r, g, b))

    @command()
    def weapon(connection, value):
        player = get_player(connection.protocol, value)
        if player.weapon_object is None:
            name = '(unknown)'
        else:
            name = player.weapon_object.name
        return '%s has a %s' % (player.name, name)

    @command("client", "cli")
    def client(connection, target):
        player = get_player(connection.protocol, target)

        info = player.client_info
        version = info.get("version", None)
        if version:
            version_string = ".".join(map(str, version))
        else:
            version_string = "Unknown"
        return "{} is connected with {} ({}) on {}".format(
            player.name,
            info.get("client", "Unknown"),
            version_string,
            info.get("os_info", "Unknown")
        )

    # optional commands
    try:
        import pygeoip
        database = pygeoip.GeoIP(os.path.join(
            cfg.config_dir, 'data/GeoLiteCity.dat'))
    except ImportError:
        print("('from' command disabled - missing pygeoip)")
    except (IOError, OSError):
        print("('from' command disabled - missing data/GeoLiteCity.dat)")
    finally:
        @command('from')
        def where_from(connection, value=None):
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
                    int(value)
                        # if this raises a ValueError, it's not a number
                    continue
                except KeyError:
                    continue
                except ValueError:
                    pass

                if not isinstance(value, str):
                    continue
                items.append(value)
            return '%s is from %s' % (player.name, ', '.join(items))
        add(where_from)

    def handle_command(connection, command, parameters):
        command = command.lower()
        try:
            command_name = _alias_map.get(command, command)
            command_func = _commands[command_name]
        except KeyError:
            return 'Unknown command'

        if not has_permission(command_func, connection):
            return "You can't use this command"

        argspec = inspect.getargspec(command_func)
        min_params = len(argspec.args) - 1 - len(argspec.defaults or ())
        max_params = len(argspec.args) - 1 if argspec.varargs is None else None
        len_params = len(parameters)

        if (len_params < min_params
                or max_params is not None and len_params > max_params):
            return format_command_error(command_func, 'Invalid number of arguments')

        msg = None

        try:
            return command_func(connection, *parameters)
        # TODO: remove all of this catching. Commands should deal with invalid
        # parameters themselves. Instead, we should catch ALL Exceptions and
        # make an attempt at displaying them nicely in format_command_error
        except KeyError:
            msg = None  # 'Invalid command'
        except TypeError as t:
            print('Command', command, 'failed with args:', parameters)
            traceback.print_exc(t)
            msg = 'Command failed'
        except CommandError as e:
            msg = e.message
        except ValueError:
            msg = 'Invalid parameters'

        return format_command_error(command_func, msg)

    def handle_input(connection, user_input):
        # for IRC and console
        return handle_command(connection, *parse_command(user_input))
