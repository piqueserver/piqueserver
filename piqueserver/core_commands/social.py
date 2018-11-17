from piqueserver.commands import command, get_player, join_arguments
from piqueserver.auth import auth, AuthError


@command()
def login(connection, password):
    """
    Log in if you're staff or a trusted member of this server
    /login <password>
    You will be kicked if a wrong password is given 3 times in a row
    """
    if connection not in connection.protocol.players:
        raise KeyError()
    try:
        user_type = auth.login(("", password))
        if user_type in connection.user_types:
            return "You're already logged in as {}".format(user_type)
        return connection.on_user_login(user_type, True)
    except AuthError:
        # TODO: refactor login retries & limit retries based on ip
        # update login retries
        if connection.login_retries is None:
            connection.login_retries = connection.protocol.login_retries - 1
        else:
            connection.login_retries -= 1
        # kick if out of retries
        if not connection.login_retries:
            connection.kick('Ran out of login attempts')
            return
        # notify with login retries
        return 'Invalid password - you have {} tries left'.format(
            connection.login_retries)


@command()
def pm(connection, value, *arg):
    """
    Send a private message to a given player
    /pm <player> <message>
    """
    player = get_player(connection.protocol, value)
    message = join_arguments(arg)
    if len(message) == 0:
        return "Please specify your message"
    player.send_chat('PM from %s: %s' % (connection.name, message))
    return 'PM sent to %s' % player.name


@command('admin')
def to_admin(connection, *arg):
    """
    Send a message to all admins currently online
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
    return 'Message sent to all admins currently online'
