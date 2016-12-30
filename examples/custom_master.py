# Copyright (c) Mathias Kaerlev 2011-2012.

# This file is part of pyspades.

# pyspades is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

# pyspades is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with pyspades.  If not, see <http://www.gnu.org/licenses/>.

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
