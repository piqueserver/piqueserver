import inspect

class InvalidPlayer(Exception):
    pass

def admin(func):
    def new_func(connection, *arg, **kw):
        if not connection.admin:
            return 'No administrator rights!'
        func(connection, *arg, **kw)
    new_func.func_name = func.func_name
    return new_func

def get_player(connection, value):
    try:
        if value.startswith('#'):
            value = int(value[1:])
            return connection.protocol.players[value][0]
        for player in connection.protocol.players.values():
            if player.name.lower().count(value):
                return player
    except (KeyError, IndexError, ValueError):
        pass
    raise InvalidPlayer()

@admin
def kick(connection, value, reason = None):
    player = get_player(connection, value)
    player.kick(reason)

@admin
def ban(connection, value, reason = None):
    player = get_player(connection, value)
    player.ban(reason)

@admin
def say(connection, *arg):
    value = ' '.join(arg)
    connection.protocol.send_chat(value)

@admin
def kill(connection, value):
    player = get_player(connection, value)
    player.kill()
    connection.protocol.send_chat('%s killed %s' % (connection.name, 
        player.name))

def votekick(connection, value, reason = None):
    player = get_player(connection, value)
    player.votekick(connection, reason)

def help(connection):
    """
    This help
    """
    names = [command.func_name for command in command_list]
    return 'Available commands: %s' % (', '.join(names))

def login(connection, password):
    """
    Login as admin
    """
    passwords = connection.protocol.admin_passwords
    if password in passwords:
        connection.admin = True
        connection.protocol.send_chat('%s logged in as admin' % connection.name)
        return None
    return 'Invalid password!'

command_list = [
    help,
    login,
    kick,
    ban,
    say,
    kill,
    votekick
]

commands = {}

for command_func in command_list:
    commands[command_func.func_name] = command_func

def handle_command(connection, command, parameters):
    try:
        command_func = commands[command]
    except KeyError:
        return 'Invalid command'
    try:
        return command_func(connection, *parameters)
    except TypeError:
        import traceback
        traceback.print_exc()
        return 'Invalid number of arguments for %s' % command
    except InvalidPlayer:
        return 'No such player'