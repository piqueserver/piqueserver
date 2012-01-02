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

from pyspades.server import ServerProtocol
from pyspades.load import VXLData
from twisted.internet import reactor

class TestProtocol(ServerProtocol):
    map = VXLData(open('../data/sinc0.vxl', 'rb'))
    version = crc32(open('../data/client.exe', 'rb').read())

PORT = 32887

reactor.listenUDP(PORT, TestProtocol())
print 'Started server on port %s...' % PORT
reactor.run()