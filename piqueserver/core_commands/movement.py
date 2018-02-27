from pyspades.common import (coordinates, to_coordinates)
from piqueserver.commands import command, CommandError, get_player


@command(admin_only=True)
def unstick(connection, player=None):
    """
    Unstick yourself or another player and inform everyone on the server of it
    /unstick [player]
    """
    if player is not None:
        player = get_player(connection.protocol, player)
    else:
        player = connection
    connection.protocol.send_chat("%s unstuck %s" %
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
    """
    do_move(connection, args, True)


@command(admin_only=True)
def move(connection, *args):
    """
    Move yourself or a given player to the specified x/y/z coordinates or sector
    /move [player] <sector> or /move [player] <x> <y> <z>
    If you're invisivible, it will happen silently.
    If the z coordinate makes the player appear underground, put them at ground level instead.
    If the x/y/z coordinate makes the player appear outside of the world bounds,
    take the bound instead
    """
    if connection not in connection.protocol.players:
        raise ValueError()
    do_move(connection, args)


def do_move(connection, args, silent=False):
    position = None
    player = None
    arg_count = len(args)

    initial_index = 1 if arg_count == 2 or arg_count == 4 else 0

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
        z = min(max(0, int(args[initial_index + 2])), connection.protocol.map.get_height(x, y) - 2)
        position = '%d %d %d' % (x, y, z)
    else:
        raise ValueError('Wrong number of parameters!')

    # no player specified
    if arg_count == 1 or arg_count == 3:
        if connection not in connection.protocol.players:
            raise ValueError()
        player = connection.name
    # player specified
    elif arg_count == 2 or arg_count == 4:
        player = args[0]

    player = get_player(connection.protocol, player)

    silent = connection.invisible or silent

    player.set_location((x, y, z))
    if connection is player:
        message = ('%s ' + ('silently ' if silent else '') + 'teleported to '
                   'location %s')
        message = message % (player.name, position)
    else:
        message = ('%s ' + ('silently ' if silent else '') + 'teleported %s '
                   'to location %s')
        message = message % (connection.name, player.name, position)
    if silent:
        connection.protocol.irc_say('* ' + message)
    else:
        connection.protocol.send_chat(message, irc=True)


@command(admin_only=True)
def where(connection, player=None):
    """
    Tell you the coordinates of yourself or of a given player
    /where [player]
    """
    if player is not None:
        connection = get_player(connection.protocol, player)
    elif connection not in connection.protocol.players:
        raise ValueError()
    x, y, z = connection.get_location()
    return '%s is in %s (%s, %s, %s)' % (
        connection.name, to_coordinates(x, y), int(x), int(y), int(z))


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


@command('tpsilent', 'tps', admin_only=True)
def tpsilent(connection, player1, player2=None):
    """
    Silently teleport a player to another player
    /tpsilent [player] <target player>
    """
    teleport(connection, player1, player2, silent=True)


@command(admin_only=True)
def fly(connection, player=None):
    """
    Enable flight
    /fly [player]
    Hold control and press space ;)
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


@command('godsilent', 'gods', admin_only=True)
def godsilent(connection, player=None):
    """
    Silently go into god mode
    /godsilent [player]
    """
    if player is not None:
        connection = get_player(connection.protocol, player)
    elif connection not in connection.protocol.players:
        return 'Unknown player: ' + player

    connection.god = not connection.god # toggle godmode

    if connection.protocol.set_god_build:
        connection.god_build = connection.god
    else:
        connection.god_build = False

    if connection.god:
        if player is None:
            return 'You have silently entered god mode'
        else:
            # TODO: Do not send this if the specified player is the one who called the command
            connection.send_chat('Someone has made you silently enter godmode!')
            return 'You made ' + connection.name + ' silently enter god mode'
    else:
        if player is None:
            return 'You have silently returned to being a mere human'
        else:
            # TODO: Do not send this if the specified player is the one who called the command
            connection.send_chat('Someone has made you silently return to being a mere human')
            return 'You made ' + connection.name + ' silently return to being a mere human'

@command(admin_only=True)
def god(connection, player=None):
    """
    Go into god mode and inform everyone on the server of it
    /god [player]
    """
    if player:
        connection = get_player(connection.protocol, player)
    elif connection not in connection.protocol.players:
        return 'Unknown player'

    connection.god = not connection.god # toggle godmode

    if connection.god:
        message = '%s entered GOD MODE!' % connection.name
    else:
        message = '%s returned to being a mere human' % connection.name
    connection.protocol.send_chat(message, irc=True)


@command('godbuild', admin_only=True)
def god_build(connection, player=None):
    """
    Place blocks that can be destroyed only by players with godmode activated
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
