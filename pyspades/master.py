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
Implementation of the 0,75 master server protocol
"""

from pyspades.loaders import Loader
from pyspades.protocol import BaseConnection
from pyspades.constants import MASTER_VERSION

from twisted.internet.defer import Deferred

PORT = 32886

MAX_SERVER_NAME_SIZE = 31
MAX_MAP_NAME_SIZE = 20
MAX_GAME_MODE_SIZE = 7

HOST = 'master.buildandshoot.com'


class AddServer(Loader):
    """The AddServer packet sent to the master server"""
    __slots__ = ['count', 'max_players', 'name', 'port', 'game_mode', 'map']

    id = 4

    def read(self, reader):
        if reader.dataLeft() == 1:
            self.count = reader.readByte(True)
        else:
            self.max_players = reader.readByte(True)
            self.port = reader.readShort(True, False)
            self.name = reader.readString()
            self.game_mode = reader.readString()
            self.map = reader.readString()

    def write(self, writer):
        if self.count is None:
            writer.writeByte(self.max_players)
            writer.writeShort(self.port, True, False)
            writer.writeString(self.name)
            writer.writeString(self.game_mode)
            writer.writeString(self.map)
        else:
            writer.writeByte(self.count, True)


add_server = AddServer()


class MasterConnection(BaseConnection):
    disconnect_callback = None
    connected = False

    def on_connect(self):
        self.connected = True
        self.send_server()

        if self.defer is not None:
            self.defer.callback(self)
            self.defer = None

    def set_count(self, value):
        add_server.count = value
        self.send_contained(add_server)

    def send_server(self):
        protocol = self.server_protocol
        add_server.count = None
        add_server.name = protocol.name[:MAX_SERVER_NAME_SIZE].encode()
        add_server.game_mode = protocol.get_mode_name()[:MAX_GAME_MODE_SIZE].encode()
        add_server.map = protocol.map_info.short_name[:MAX_MAP_NAME_SIZE].encode()
        add_server.port = protocol.host.address.port
        add_server.max_players = protocol.max_players
        self.send_contained(add_server)

    def on_disconnect(self):
        if self.defer is not None:
            self.defer.errback(self)
            self.defer = None
        callback = self.disconnect_callback
        if callback is not None:
            callback()
        self.disconnect_callback = None


def get_master_connection(protocol):
    defer = Deferred()
    connection = protocol.connect(MasterConnection, HOST, PORT, MASTER_VERSION)
    connection.server_protocol = protocol
    connection.defer = defer
    return defer
