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

from pyspades.loaders cimport Loader
from pyspades.bytes cimport ByteReader, ByteWriter

_client_loaders = {}
_server_loaders = {}

def register_packet(loader=None, server=True, client=True, extension=None):
    """register a packet

    >>> @register_packet()
    ... class SomePacket(Loader):
    ...     pass

    Optionally can be used as function too, but this is discouraged unless you
    need to do this (the default pyspades loaders need this, as they are
    defined in C++ code):

    >>> class AnotherPacket(Loader):
    ...     pass
    ...
    >>> register_packet(AnotherPacket, server=False)

    Additionally you can specify if only the server or client can send this
    packet. This is only useful in a few rare cases, so these are set to
    ``True`` by default.

    Arguments:
        server (bool, optional): This packet can be sent by the server. True by
            default.
        client (bool, optional): This packet can be sent by the client. True by
            default
        extension (int, optional): The extension id this packet belongs to, if any

    Raises:
        KeyError: If the packet's ID has already been registered
    """

    # Rationale:
    # In the past, the packet list was static and contained no meta-information
    # about the packet this was fine, because there was really only one
    # version.  However, it is foreseeable from current developments that there
    # will be several played protocol versions and a number of clients could
    # have different feature sets that must be queried at runtime. Hence it is
    # useful to annotate packets with some kind of runtime information.

    # It is not known if full-blown multiple protocol version support will ever
    # be realized, but this is one step along the way. It might be a massive
    # miscalculation and be technical debt for the rest of the projects
    # lifetime, but only time will tell

    def register(cls):
        # Having to handle the two loader dicts separate isn't very nice, but I
        # you can't avoid it whithout making things more complicated somewhere
        # else.
        # This is needed because certain packets (e.g. HitPacket and SetHP) in
        # likely a legendary case of premature optimisation (or because the
        # packet IDs had to be contigous in voxlap?) share packet IDs, but have
        # different meaning and format depending on who sends them
        # Since this library tries to work as both a Server and Client
        # implementation, both are always evaluated

        if client:
            if cls.id in _client_loaders:
                msg = ("Tried to register client packet '{!r}', but a packet "
                       "with that id ({}) already exists.".format(cls, cls.id))
                raise KeyError(msg)
            _client_loaders[cls.id] = cls

        if server:
            if cls.id in _server_loaders:
                msg = ("Tried to register server packet '{!r}', but a packet "
                       "with that id ({}) already exists.".format(cls, cls.id))
                raise KeyError(msg)
            _server_loaders[cls.id] = cls

        return cls

    if loader:
        # Call the registration function directly if we are being called as a
        # function, not as a decorator
        register(loader)

    return register


def load_server_packet(data):
    return load_contained_packet(data, _server_loaders)

def load_client_packet(data):
    return load_contained_packet(data, _client_loaders)

cdef inline Loader load_contained_packet(ByteReader data, dict table):
    type_ = data.readByte(True)
    return table[type_](data)

_packet_handlers = {}

def register_packet_handler(loader):
    def register_handler(function):
        _packet_handlers[loader.id] = function
        return function
    return register_handler

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
