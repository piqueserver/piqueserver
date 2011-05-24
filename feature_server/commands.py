import shlex

def help(connection):
    """
    This help.
    """
    return 'Available commands: (None).'  

command_list = [
    help
]

def handle_command(connection, command, parameters):
    pass