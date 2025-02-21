from pyspades.common import (coordinates, to_coordinates)
from piqueserver.commands import (command, CommandError, get_player,
                                  PermissionDenied, player_only, target_player)


@command(admin_only=True)
@target_player
def unstick(connection, player):
    """
    Unstick yourself or another player and inform everyone on the server of it
    /unstick [player]
    """
    connection.protocol.broadcast_chat("%s unstuck %s" %
                                  (connection.name, player.name), irc=True)
    player.set_location_safe(player.get_location())


@command('moves', admin_only=True)
def move_silent(connection, *args):
    """
    Silently move yourself or a given player to the specified x/y/z coordinates or sector
    /moves [player] <sector> or /moves [player] <x> <y> <z>
    If the z coordinate makes the player appear underground, put them at ground level instead.
    If the x/y/z coordinate makes the player appear outside of the world bounds,
    take the bound instead

    You can only move other players if you are admin or have the move_others right
    """
    do_move(connection, args, True)


@command(admin_only=True)
@player_only
def move(connection, *args):
    """
    Move yourself or a given player to the specified x/y/z coordinates or sector
    /move [player] <sector> or /move [player] <x> <y> <z>
    If you're invisible, it will happen silently.
    If the z coordinate makes the player appear underground, put them at ground level instead.
    If the x/y/z coordinate makes the player appear outside of the world bounds,
    take the bound instead

    You can only move other players if you are admin or have the move_others right
    """
    do_move(connection, args)

def validate_and_parse_args(args):
    """
    Validate the argument count and determine the initial index.
    
    :params:
    args: the movement arguments.
    
    return: length of args, the inital index based on args
    """
    arg_count = len(args)
    if arg_count not in {1, 2, 3, 4}:
        raise ValueError('Wrong number of parameters!')
    initial_index = 1 if arg_count in {2, 4} else 0
    return arg_count, initial_index


def determine_movement_target(connection, args, arg_count, initial_index):
    """
    Determine the movement target as either a sector or coordinates.
    
    :params:
    connection: the connection to the server
    args: movement arguments
    arg_count: length of movement arguments
    initial_index: the start index


    return: the player position coordinates
    """
    if arg_count in {1, 2}:  # Target sector
        x, y = coordinates(args[initial_index])
        x += 32
        y += 32
        z = connection.protocol.map.get_height(x, y) - 2
        position = args[initial_index].upper()
    else:  # Target coordinates
        x = min(max(0, int(args[initial_index])), 511)
        y = min(max(0, int(args[initial_index + 1])), 511)
        z = min(max(0, int(args[initial_index + 2])), connection.protocol.map.get_height(x, y) - 2)
        position = '%d %d %d' % (x, y, z)
    return x, y, z, position


def determine_player(connection, args, arg_count):
    """
    Determine whether the move is for self or another player.

    :params:
    connection: the connection to the server
    args: the movement arguments
    arg_count: the length of the movements arguments

    return: the first movement argument or player name.
    """
    if arg_count in {1, 3}:  # Move self
        if connection not in connection.protocol.players.values():
            raise ValueError("Both player and target player are required")
        return connection.name
    elif arg_count in {2, 4}:  # Move other
        if not (connection.admin or connection.rights.move_others):
            raise PermissionDenied("moving other players requires the move_others right")
        return args[0]
    return None


def do_move(connection, args, silent=False):
    """
    Moves a player to a specified location.

    :params:
    connection: The player issuing the move command
    args: The movement target, either a sector or specific coordinates
    silent: Whether the move should be silent.
    """
    arg_count, initial_index = validate_and_parse_args(args)
    x, y, z, position = determine_movement_target(connection, args, arg_count, initial_index)
    player_name = determine_player(connection, args, arg_count)
    
    player = get_player(connection.protocol, player_name)
    silent = connection.invisible or silent
    player.set_location((x, y, z))
    
    if connection is player:
        message = ('%s ' + ('silently ' if silent else '') + 'teleported to location %s') % (player.name, position)
    else:
        message = ('%s ' + ('silently ' if silent else '') + 'teleported %s to location %s') % (connection.name, player.name, position)
    
    if silent:
        connection.protocol.irc_say('* ' + message)
    else:
        connection.protocol.broadcast_chat(message, irc=True)

@command(admin_only=True)
@target_player
def where(connection, player):
    """
    Tell you the coordinates of yourself or of a given player
    /where [player]
    """
    x, y, z = player.get_location()
    return '%s is in %s (%s, %s, %s)' % (
        player.name, to_coordinates(x, y), int(x), int(y), int(z))


@command('teleport', 'tp', admin_only=True)
def teleport(connection, player1, player2=None, silent=False):
    """
    Teleport yourself or a given player to another player
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
        if connection not in connection.protocol.players.values():
            raise ValueError("Both player and target player are required")
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
        connection.protocol.broadcast_chat(message, irc=True)


@command('tpsilent', 'tps', admin_only=True)
def tpsilent(connection, player1, player2=None):
    """
    Silently teleport a player to another player
    /tpsilent [player] <target player>
    """
    teleport(connection, player1, player2, silent=True)


@command(admin_only=True)
@target_player
def fly(connection, player):
    """
    Enable flight
    /fly [player]
    Hold control and press space ;)
    """
    protocol = connection.protocol
    player.fly = not player.fly

    message = 'now flying' if player.fly else 'no longer flying'
    player.send_chat("You're %s" % message)
    if connection is not player and connection in protocol.players.values():
        connection.send_chat('%s is %s' % (player.name, message))
    protocol.irc_say('* %s is %s' % (player.name, message))
