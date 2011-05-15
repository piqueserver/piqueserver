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

isClient = None
mapBytes = 0
packets = 0
map_data = {}
is_relay = False
sequence = None

from pyspades.bytereader import ByteReader

chunks = {}

current_id = 0
def write_packet(data):
    global current_id
    open('packets/%s.dat' % current_id, 'wb').write(str(data))
    current_id += 1