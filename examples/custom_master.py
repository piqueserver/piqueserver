"""
Custom master server connection. Idea from "izzy".
Use this if you've lost connection to the master server on a normal server.exe
server.
"""

# izzy's IP. Set to "None" if the current IP should be fetched
IP = '184.82.238.20'

from pyspades.master import get_master_connection
from twisted.internet import reactor

def connected(connection):
    print 'connected!', connection
    reactor.callLater(5, connection.set_count, 20)

get_master_connection('Servername here!', 32, '184.82.238.20'
    ).addCallback(connected)

print 'Connecting to master...'
reactor.run()