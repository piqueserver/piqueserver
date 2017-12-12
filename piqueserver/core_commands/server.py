from __future__ import print_function, unicode_literals
from piqueserver.commands import command, join_arguments

print("core.server.py")

@command('servername', admin_only=True)
def server_name(connection, *arg):
    name = join_arguments(arg)
    protocol = connection.protocol
    protocol.config['name'] = name
    protocol.update_format()
    message = "%s changed servername to to '%s'" % (connection.name, name)
    print(message)
    connection.protocol.irc_say("* " + message)
    if connection in connection.protocol.players:
        return message


@command('server')
def server_info(connection):
    protocol = connection.protocol
    msg = 'You are playing on "%s"' % protocol.name
    if protocol.identifier is not None:
        msg += ' at %s' % protocol.identifier
    return msg


@command()
def version(connection):
    return 'Server version is "%s"' % connection.protocol.server_version


@command()
def scripts(connection):
    scripts = connection.protocol.config.get('scripts', [])
    return 'Scripts enabled: %s' % (', '.join(scripts))


@command('togglemaster', 'master', admin_only=True)
def toggle_master(connection):
    protocol = connection.protocol
    protocol.set_master_state(not protocol.master)
    message = ("toggled master broadcast %s" % ['OFF', 'ON'][
        int(protocol.master)])
    protocol.irc_say("* %s " % connection.name + message)
    if connection in connection.protocol.players:
        return "You " + message
