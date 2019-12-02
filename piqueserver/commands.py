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

import traceback
import inspect
import warnings
from collections import namedtuple
import textwrap
import functools
from typing import Dict, List, Callable

from twisted.logger import Logger

from pyspades.common import escape_control_codes
from pyspades.player import parse_command

_commands = {}
_alias_map = {}
_rights = {}  # type: Dict[str, List[str]]

log = Logger()

class CommandError(Exception):
    pass


class PermissionDenied(Exception):
    pass


def command(name=None, *aliases,
            admin_only=False) -> Callable[[Callable], Callable]:
    """
    Register a new command.

    The command will be accessible as `/function_name` unless a name or alias
    is specified.

    >>> @command()
    ... def some_command(x):
    ...     pass

    Optional names and aliases:

    >>> @command("name", "alias1", "alias2")
    ... def some_command(x):
    ...     pass
    """
    def decorator(function) -> Callable[..., str]:
        function.user_types = set()
        if admin_only:
            function.user_types.add("admin")

        nonlocal name
        if name is None:
            name = function.__name__

        function.command_name = name

        _commands[name] = function

        if aliases:
            function.aliases = []

            for alias in aliases:
                _alias_map[alias] = name

        return function
    return decorator


def add(func: Callable) -> None:
    """
    Function to add a command from scripts. Deprecated
    """
    warnings.warn(
        '@add is deprecated, use @command()',
        DeprecationWarning)
    command()(func)


def name(name: str) -> Callable:
    """
    Give the command a new name. Deprecated
    """
    warnings.warn(
        '@name is deprecated, use @command("name")',
        DeprecationWarning)

    def dec(func: Callable) -> Callable:
        func.__name__ = name
        return func
    return dec


def alias(name: str) -> Callable:
    """
    add a new alias to a command. Deprecated
    """
    warnings.warn(
        '@alias is deprecated, use @command("name", "alias1", "alias2")',
        DeprecationWarning)

    def dec(func: Callable) -> Callable:
        try:
            func.aliases.append(name)
        except AttributeError:
            func.aliases = [name]
        return func
    return dec


def restrict(*user_types: List[str]) -> Callable:
    """
    restrict the command to only be used by a specific type of user

    >>> @restrict("admin", "guard")
    ... @command()
    ... def some_command(x):
    ...     pass
    """
    def decorator(function: Callable) -> Callable:
        function.user_types = set(*user_types)
        return function
    return decorator


def has_permission(f, connection):
    if not f.user_types:
        return True
    elif f.command_name in connection.rights:
        return True
    elif connection.admin:
        return True
    else:
        return False


CommandHelp = namedtuple("CommandHelp", ["description", "usage", "info"])


def get_command_help(command_func: Callable) -> CommandHelp:
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


def format_command_error(command_func: Callable, message: str, exception:
                         Exception=None) -> str:
    """format a help message for a given command"""
    command_help = get_command_help(command_func)

    if command_help.usage:
        return "{}\nUsage: {}".format(message, command_help.usage)
    else:
        return message

# it might seem unecesary to reimplement half of the dict data type for
# _rights, but previously this attribute was accessed and modified from
# various places and that made things more confusing than the needed to be


def add_rights(user_type: str, command_name: str) -> None:
    """
    Give the user type a new right

    >>> add_rights("knights", "say_ni")
    """
    _rights.setdefault(user_type, []).append(command_name)


def get_rights(user_type: str) -> List[str]:
    """
    Get a list of rights a specific user type has.

    >>> add_rights("knights", "say_ni")
    >>> get_rights("knights")
    ["say_ni"]
    >>> get_rights("arthur")
    []
    """
    r = _rights.get(user_type, [])
    return r


def update_rights(rights: Dict):
    """
    Update the rights of all users according to the input dictionary. This
    is currently only here for when the config needs to be reloaded.

    >>> update_rights({"knights": ["say_ni"]})
    >>> get_rights("knights")
    ["say_ni"]
    """
    _rights.update(rights)


def admin(func: Callable) -> Callable:
    """
    Shorthand for @restrict("admin"). Mainly exists for backwards
    compatibility with pyspades scripts.

    >>> @admin
    ... @command()
    ... def some_command(x):
    ...     pass
    """
    return restrict('admin')(func)


def player_only(func: Callable):
    """This recorator restricts a command to only be runnable by players
    connected to the server, not via other places such as, say, the console.

    >>> @command()
    ... @player_only
    ... def some_command(x):
    ...     pass
    """
    @functools.wraps(func)
    def _decorated(connection, *args, **kwargs):
        if connection not in connection.protocol.players.values():
            raise CommandError("only players can't use this command")
        func(connection, *args, **kwargs)
    return _decorated

def target_player(func: Callable):
    """This decorator converts first argument of a command to a `piqueserver.FeatureConnection`.
       It's intended for commands which accept single argument for target player eg. /fly [player].
       It implicitly uses invoker as target if no arguments are provided.
       It uses first argument are player name or id for targetting.
       It forces non-player invokers to provide player argument.

    >>> @command()
    ... @target_player
    ... def fly(connection, target):
    ...     target.fly = True
    ...     pass
    """
    @functools.wraps(func)
    def _decorated(connection, *args, **kwargs):
        is_player = connection in connection.protocol.players.values()
        # implicitly set target to invoker if no args
        if len(args) == 0 and is_player:
            args = (connection,)
        # try and use first arg as player name or id to target
        elif len(args) > 0:
            args = (get_player(connection.protocol, args[0]), *args[1:])
        # console or irc invokers are required to provide a target
        else:
            raise ValueError("Target player is required")
        return func(connection, *args, **kwargs)
    return _decorated

def get_player(protocol, value: str, spectators=True):
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
    team_1 = connection.protocol.team_1
    team_2 = connection.protocol.team_2
    team_spectator = connection.protocol.team_spectator
    if value == team_1.name.lower():
        return connection.protocol.team_1
    elif value == team_2.name.lower():
        return connection.protocol.team_2
    elif value == team_spectator.name.lower():
        return connection.protocol.spectator_team
    elif value == '1':
        return connection.protocol.team_1
    elif value == '2':
        return connection.protocol.team_2
    elif value == 'spec':
        return connection.protocol.spectator_team
    raise ValueError('Invalid Team')


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


def handle_command(connection, command, parameters):
    """
    Public facing function to run a command, given the connection, a command
    name, and a list of parameters.

    Will log the command.
    """
    result = _handle_command(connection, command, parameters)

    if result == False:
        parameters = ['***'] * len(parameters)
    log_message = '<{}> /{} {}'.format(connection.name, command,
                                       ' '.join(parameters))
    if result:
        log_message += ' -> %s' % result
    log.info(escape_control_codes(log_message))

    return result

def _handle_command(connection, command, parameters):
    command = command.lower()
    try:
        command_name = _alias_map.get(command, command)
        command_func = _commands[command_name]
    except KeyError:
        return 'Unknown command'

    if not has_permission(command_func, connection):
        return "You can't use this command"

    argspec = inspect.getfullargspec(command_func)
    min_params = len(argspec.args) - 1 - len(argspec.defaults or ())
    max_params = len(argspec.args) - 1 if argspec.varargs is None else None
    len_params = len(parameters)

    if (len_params < min_params
            or max_params is not None and len_params > max_params):
        return format_command_error(
            command_func, 'Invalid number of arguments')

    msg = None

    try:
        return command_func(connection, *parameters)
    # TODO: remove all of this catching. Commands should deal with invalid
    # parameters themselves. Instead, we should catch ALL Exceptions and
    # make an attempt at displaying them nicely in format_command_error
    except KeyError:
        msg = None  # 'Invalid command'
        traceback.print_exc()
    except TypeError:
        print('Command', command, 'failed with args:', parameters)
        traceback.print_exc()
        msg = 'Command failed'
    except CommandError as e:
        msg = str(e)
    except PermissionDenied as e:
        msg = 'You can\'t do that: {}'.format(str(e))
    except ValueError as e:
        msg = str(e) if e.args else "Invalid parameters"

    return format_command_error(command_func, msg)


def handle_input(connection, user_input):
    # for IRC and console
    return handle_command(connection, *parse_command(user_input))
