# Copyright (c) Mathias Kaerlev 2011.

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
Client implementation - NOT DONE YET AT ALL!
"""

from twisted.internet.protocol import DatagramProtocol
from pyspades.bytereader import ByteReader

class ClientProtocol(DatagramProtocol):
    firstTime = True
    def __init__(self, host, port):
        self.host, self.port = host, port
    
    def startProtocol(self):
        self.transport.connect(self.host, self.port)
        value = '\x00\x00\x00\x00'
        self.transport.write(hello)
    
    def write_packet(self, packet_id):
        pass
    
    def datagramReceived(self, data, (host, port)):
        reader = ByteReader(data)
        if self.firstTime:
            self.transport.write(data[0] + answer[1:])
            self.firstTime = False