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

import struct

def make_server_identifier(ip, port = 32887):
    a, b, c, d = ip.split('.')
    a = int(a)
    b = int(b)
    c = int(c)
    d = int(d)
    return 'aos://%s:%s' % (a | (b << 8) | (c << 16) | (d << 24), port)

def get_server_details(value):
    if not value.startswith('aos://'):
        raise ValueError('invalid server identifier')
    splitted = value[6:].split(':')
    if len(splitted) == 1:
        host = int(splitted[0])
        port = 32887
    else:
        host, port = splitted
        host = int(host)
        port = int(port)
    a = host & 0xFF
    b = (host & 0xFF00) >> 8
    c = (host & 0xFF0000) >> 16
    d = (host & 0xFF000000) >> 24
    return ('%s.%s.%s.%s' % (a, b, c, d), port)

if __name__ == '__main__':
    import sys
    args = sys.argv[1:]
    command = args[0]
    if command == 'readpacket':
        from pyspades.packet import Packet
        new_packet = Packet()
        new_packet.read(eval(' '.join(args[1:])))
        print new_packet.items
