from piqueserver.commands import command, get_player


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


@command()
def weapon(connection, value):
    player = get_player(connection.protocol, value)
    if player.weapon_object is None:
        name = '(unknown)'
    else:
        name = player.weapon_object.name
    return '%s has a %s' % (player.name, name)


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


@command(admin_only=True)
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
