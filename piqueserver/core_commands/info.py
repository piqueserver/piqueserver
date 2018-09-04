from piqueserver.commands import command, _commands, has_permission, get_player, get_command_help


@command()
def streak(connection):
    """
    Tell your current kill streak
    /streak
    """
    if connection not in connection.protocol.players:
        raise KeyError()
    return ('Your current kill streak is %s. Best is %s kills' %
            (connection.streak, connection.best_streak))


@command()
def ping(connection, value=None):
    """
    Tell your current ping (time for your actions to be received by the server)
    /ping
    """
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
    Show you the server rules
    /rules
    """
    if connection not in connection.protocol.players:
        raise KeyError()
    lines = connection.protocol.rules
    if lines is None:
        return
    connection.send_lines(lines)


@command()
def commands(connection):
    """
    Print all available commands
    /commands
    """
    # Compact and simple output for admins
    if connection.admin:
        names = [command.command_name for command in _commands.values()
                 if has_permission(command, connection)]
        return 'Available commands: %s' % (', '.join(names))
    # More helpful output for regular players
    lines = []
    for cmd in _commands.values():
        if not has_permission(cmd, connection):
            continue
        desc, _, _ = get_command_help(cmd)
        lines.append("/{} {}".format(cmd.command_name, desc))
    connection.send_lines(lines)


@command("help")
def help_command(connection, command_name=None):
    """
    Gives description and usage info for a command
    /help <command_name>
    """
    # Querying usage for a specific command
    if command_name:
        if command_name not in _commands:
            return 'Unknown command'
        command_func = _commands[command_name]
        desc, usage, _ = get_command_help(command_func)
        return 'Description: {}\n Usage: {}'.format(desc, usage)
    # Output help if present in config
    if connection.protocol.help:
        return connection.send_lines(connection.protocol.help)
