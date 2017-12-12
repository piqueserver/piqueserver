from piqueserver.commands import command, get_player, join_arguments


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
