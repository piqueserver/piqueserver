from piqueserver.commands import command, _commands, has_permission, get_player


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
