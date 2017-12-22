from __future__ import print_function, unicode_literals
from piqueserver.commands import command, join_arguments

# Does this affect master server list?
@command('servername', admin_only=True)
def server_name(connection, *arg):
    """
    Modifies the server name
    /servername <new-name>
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
    Tells you the name of the server and it's aos:// URI
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
    Tells you this server's piqueserver version
    /version
    """
    return 'Server version is "%s"' % connection.protocol.server_version


@command()
def scripts(connection):
    """
    Tells you which scripts are enabled on this server currently
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
    Toggles connection to the master server list
    /togglemaster
    """
    protocol = connection.protocol
    protocol.set_master_state(not protocol.master)
    message = ("toggled master broadcast %s" % ['OFF', 'ON'][
        int(protocol.master)])
    protocol.irc_say("* %s " % connection.name + message)
    if connection in connection.protocol.players:
        return "You " + message
