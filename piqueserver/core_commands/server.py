import random
import sys

from twisted.logger import Logger

from piqueserver.commands import command, join_arguments

log = Logger()


@command('servername', admin_only=True)
def server_name(connection, *arg):
    """
    Change the server name until it restarts
    /servername <new-name>
    Also affects the master list
    """
    if not arg:
        raise ValueError("no argument given")
    name = join_arguments(arg)
    protocol = connection.protocol
    protocol.set_server_name(name)
    message = "%s changed servername to '%s'" % (connection.name, name)
    log.info(message)
    connection.protocol.irc_say("* " + message)
    if connection in connection.protocol.players.values():
        return message
    return None


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
    import piqueserver
    return 'Server version is "{}" on "{}"'.format(
        piqueserver.__version__, sys.platform)


@command()
def scripts(connection):
    """
    Tell you which scripts are enabled on this server currently
    /scripts
    """
    scripts = connection.protocol.config.get('scripts', [])
    if not scripts:
        return 'No scripts are enabled currently'
    return 'Scripts enabled: %s' % (', '.join(scripts))


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
    if connection in connection.protocol.players.values():
        return "You " + message
