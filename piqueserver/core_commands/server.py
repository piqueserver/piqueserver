from __future__ import print_function, unicode_literals
from piqueserver.commands import command, join_arguments

@command('servername', admin_only=True)
def server_name(connection, *arg):
    """
    Change the server name until it restarts
    /servername <new-name>
    Also affects the master list
    """
    name = join_arguments(arg)
    protocol = connection.protocol
    protocol.config['name'] = name
    protocol.update_format()
    message = "%s changed servername to '%s'" % (connection.name, name)
    print(message)
    connection.protocol.irc_say("* " + message)
    if connection in connection.protocol.players:
        return message


@command('server')
def server_info(connection):
    """
    Tell you the name of this server and its aos:// URI
    /server
    """
    protocol = connection.protocol
    msg = 'You are playing on "%s"' % protocol.name
    if protocol.identifier is not None:
        msg += ' at %s' % protocol.identifier
    return msg


@command()
def version(connection):
    """
    Tell you this server's piqueserver version
    /version
    """
    return 'Server version is "%s"' % connection.protocol.server_version


@command()
def scripts(connection):
    """
    Tell you which scripts are enabled on this server currently
    /version
    """
    scripts = connection.protocol.config.get('scripts', [])
    if len(scripts) > 0:
        return 'Scripts enabled: %s' % (', '.join(scripts))
    else:
        return 'No scripts are enabled currently'


@command('togglemaster', 'master', admin_only=True)
def toggle_master(connection):
    """
    Toggle connection to the master server list
    /togglemaster
    """
    protocol = connection.protocol
    protocol.set_master_state(not protocol.master)
    message = ("toggled master broadcast %s" % ['OFF', 'ON'][
        int(protocol.master)])
    protocol.irc_say("* %s " % connection.name + message)
    if connection in connection.protocol.players:
        return "You " + message
