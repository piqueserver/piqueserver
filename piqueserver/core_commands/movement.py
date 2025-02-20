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


def do_move(connection, args, silent=False):
    # R1: Allow a player to move themselves.
    # R2: Allow an admin or a player with "move_others" permission to move another player.
    # R3: Correctly interpret movement arguments as either a sector or coordinates.
    # R4: If the "silent" flag is set, or if the player is invisible, the movement must be silent.
    # R5: If movement args are incorrect must raise a "ValueError".
    # R6: If a player tries to move another player without permission then must raise a "PermissionDenied" error.
    # R7: The function must correctly update the player’s location.
    # R8: If a player is not found, the function must handle the error properly.
    # R9: If movement is successful, a message must be sent.

    position = None
    player = None
    arg_count = len(args)

    initial_index = 1 if arg_count == 2 or arg_count == 4 else 0

    # R3: Determine movement target
    # the target position is a <sector>
    if arg_count == 1 or arg_count == 2:
        x, y = coordinates(args[initial_index])
        x += 32
        y += 32
        z = connection.protocol.map.get_height(x, y) - 2
        position = args[initial_index].upper()
    # the target position is <x> <y> <z>
    elif arg_count == 3 or arg_count == 4:
        x = min(max(0, int(args[initial_index])), 511)
        y = min(max(0, int(args[initial_index + 1])), 511)
        z = min(max(0, int(args[initial_index + 2])),
                connection.protocol.map.get_height(x, y) - 2)
        position = '%d %d %d' % (x, y, z)
    else:
        # R5: Invalid argument count should raise ValueError
        raise ValueError('Wrong number of parameters!')

    # R1, R2: Determine if the move is for self or another player
    # no player specified
    if arg_count == 1 or arg_count == 3:
        # must be run by a player in this case because moving self
        if connection not in connection.protocol.players.values():
            # R8: Handle missing player error
            raise ValueError("Both player and target player are required")
        player = connection.name
    # player specified
    elif arg_count == 2 or arg_count == 4:
        # R6: Check permission before moving another player
        if not (connection.admin or connection.rights.move_others):
            raise PermissionDenied("moving other players requires the move_others right")
        player = args[0]

    # R8: Retrieve target player
    player = get_player(connection.protocol, player)

    # R4: Determine if movement should be silent
    silent = connection.invisible or silent

    # R7: Move the player
    player.set_location((x, y, z))

    # R9: Generate movement message
    if connection is player:
        message = ('%s ' + ('silently ' if silent else '') + 'teleported to '
                   'location %s')
        message = message % (player.name, position)
    else:
        message = ('%s ' + ('silently ' if silent else '') + 'teleported %s '
                   'to location %s')
        message = message % (connection.name, player.name, position)

    # R9: Send movement message
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
