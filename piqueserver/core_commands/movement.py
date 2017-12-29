from pyspades.common import (coordinates, to_coordinates)
from piqueserver.commands import command, get_player


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


@command('goto', admin_only=True)
def go_to(connection, value):
    """
    Go to a specified sector (e.g. A5) and inform everyone on the server of it
    /goto <sector>
    If you're invisivible, it will happen silenty
    """
    if connection not in connection.protocol.players:
        raise KeyError()
    move(connection, connection.name, value, silent=connection.invisible)


@command('gotos', admin_only=True)
def go_to_silent(connection, value):
    """
    Silently go to a specified sector
    /gotos <sector>
    """
    if connection not in connection.protocol.players:
        raise KeyError()
    move(connection, connection.name, value, True)


@command(admin_only=True)
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
    if player is not None:
        connection = get_player(connection.protocol, player)
    elif connection not in connection.protocol.players:
        return 'Unknown player: ' + player

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
