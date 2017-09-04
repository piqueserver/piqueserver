# Copyright (c) Mathias Kaerlev 2011-2012.

# This file is part of pyspades.

# pyspades program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

# pyspades is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with pyspades.  If not, see <http://www.gnu.org/licenses/>.

from pyspades.common import *
from pyspades.loaders cimport Loader
from pyspades import debug
from pyspades.bytes cimport ByteReader, ByteWriter

from pyspades import contained

CONTAINED_LIST = [
    contained.PositionData,
    contained.OrientationData,
    contained.WorldUpdate,
    contained.InputData,
    contained.WeaponInput,
    contained.HitPacket,
    contained.GrenadePacket,
    contained.SetTool,
    contained.SetColor,
    contained.ExistingPlayer,
    contained.ShortPlayerData,
    contained.MoveObject,
    contained.CreatePlayer,
    contained.BlockAction,
    contained.BlockLine,
    contained.StateData,
    contained.KillAction,
    contained.ChatMessage,
    contained.MapStart,
    contained.MapChunk,
    contained.PlayerLeft,
    contained.TerritoryCapture,
    contained.ProgressBar,
    contained.IntelCapture,
    contained.IntelPickup,
    contained.IntelDrop,
    contained.Restock,
    contained.FogColor,
    contained.WeaponReload,
    contained.ChangeTeam,
    contained.ChangeWeapon,
    contained.HandShakeInit,
    contained.HandShakeReturn,
    contained.VersionRequest,
    contained.VersionResponse,
]

CONTAINED_LOADERS = {}

for item in CONTAINED_LIST:
    CONTAINED_LOADERS[item.id] = item

SERVER_LOADERS = CONTAINED_LOADERS.copy()
for item in (contained.SetHP,):
    SERVER_LOADERS[item.id] = item

CLIENT_LOADERS = CONTAINED_LOADERS.copy()
for item in (contained.HitPacket,):
    CLIENT_LOADERS[item.id] = item

def load_server_packet(data):
    return load_contained_packet(data, SERVER_LOADERS)

def load_client_packet(data):
    return load_contained_packet(data, CLIENT_LOADERS)

cdef inline Loader load_contained_packet(ByteReader data, dict table):
    type_ = data.readByte(True)
    return table[type_](data)

_packet_handlers = {}

def register_packet_handler(loader):
    def handler_wrapper(function):
        _packet_handlers[loader.id] = function
        return function
    return handler_wrapper

def call_packet_handler(self, loader):
    contained = load_client_packet(ByteReader(loader.data))
    try:
        handler = _packet_handlers[contained.id]
    except KeyError:
        # an invalid ID was sent
        pass
    finally:
        # we call the handler in the finally clause so we don't
        # accidentally ignore KeyErrors the handler raises
        handler(self, contained)
