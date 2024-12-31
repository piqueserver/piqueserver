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

from __future__ import annotations
from dataclasses import dataclass
import socket
from typing import TYPE_CHECKING, Any, Callable, List, TypedDict

from twisted.internet import reactor
from twisted.logger import Logger
from pyspades.loaders import Loader
from pyspades.protocol import BaseConnection
from pyspades.constants import MASTER_VERSION

if TYPE_CHECKING:
    from pyspades.server import ServerProtocol

MAX_SERVER_NAME_SIZE = 31
MAX_MAP_NAME_SIZE = 20
MAX_GAME_MODE_SIZE = 7

log = Logger()

@dataclass
class MasterHostDescriptor:
    host: str
    port: int

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
    server_protocol: ServerProtocol
    descriptor: MasterHostDescriptor
    on_master_connect: Callable[[], None] | None
    on_master_disconnect: Callable[[], None] | None

    def __init__(self, protocol: Any, peer: Any):
        super().__init__(protocol, peer)
        self.was_once_connected: bool = False
        self.connected: bool = False

    def on_connect(self):
        self.connected = True
        self.was_once_connected = True
        self.update_server()

        if callback := self.on_master_connect:
            callback()

    def on_disconnect(self):
        self.connected = False

        if callback := self.on_master_disconnect:
            callback()

    def update_player_count(self, value: int):
        add_server.count = value
        self.send_contained(add_server)

    def update_server(self):
        protocol = self.server_protocol
        add_server.count = None
        add_server.name = protocol.name[:MAX_SERVER_NAME_SIZE].encode()
        add_server.game_mode = protocol.get_mode_name()[:MAX_GAME_MODE_SIZE].encode()
        add_server.map = protocol.map_info.short_name[:MAX_MAP_NAME_SIZE].encode()
        add_server.port = protocol.host.address.port
        add_server.max_players = protocol.max_players
        self.send_contained(add_server)

class MasterPool:
    def __init__(
        self,
        protocol: ServerProtocol, *,
        reconnect_interval: int=30,
    ) -> None:
        self.descriptors: List[MasterHostDescriptor] = []
        self.clients: List[MasterConnection] = []
        self.protocol = protocol

    def add_descriptor(self, host: str, port: int):
        descriptor = MasterHostDescriptor(host=host, port=port)
        self.descriptors += [descriptor]

    def add_client(self, desc: MasterHostDescriptor):
        connection = self.protocol.connect(
            MasterConnection, desc.host, desc.port, MASTER_VERSION)

        connection.server_protocol = self.protocol
        connection.descriptor = desc
        connection.on_master_connect = \
            lambda: self.on_master_connect(connection)
        connection.on_master_disconnect = \
            lambda: self.on_master_disconnect(connection)

        self.clients += [connection]

    def remove_client(self, client: MasterConnection):
        if client.connected:
            client.on_master_disconnect = None
            client.disconnect()

        self.clients.remove(client)

    def up(self):
        for desc in self.descriptors:
            try:
                self.add_client(desc)
            except OSError as error:
                log.error(
                    'Could not add master client [{host}:{port}]: {error}',
                    host=desc.host,
                    port=desc.port,
                    error=error,
                )

    def down(self):
        for client in self.clients:
            self.remove_client(client)

    def reset(self):
        self.down()
        self.descriptors = []

    def on_master_connect(self, client: MasterConnection):
        if (count := self.protocol.get_player_count()) > 0:
            client.update_player_count(count)

        log.info(
            'Connection to [{host}:{port}] was successful',
            host=client.descriptor.host,
            port=client.descriptor.port,
        )

    def on_master_disconnect(self, client: MasterConnection):
        if client.was_once_connected:
            message = 'Disconnected from [{host}:{port}], reconnecting in 60s'
        else:
            # connection failure instead of disconnect
            message = 'Connection to [{host}:{port}] failed, retrying in 60s'

        log.info(
            message,
            host=client.descriptor.host,
            port=client.descriptor.port,
        )

        self.remove_client(client)
        reactor.callLater(60, lambda: self.add_client(client.descriptor))

    def update_server(self):
        for client in self.clients:
            client.update_server()

    def update_player_count(self, count: int):
        for client in self.clients:
            client.update_player_count(count)
