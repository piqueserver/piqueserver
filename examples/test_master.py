from pyspades.master import get_master_connection
from twisted.internet import reactor

def connected(connection):
    print 'connected!', connection

get_master_connection('pyspades WIP test', 20).addCallback(connected)

print 'Connecting to master...'
reactor.run()