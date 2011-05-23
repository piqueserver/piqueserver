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

import struct

def make_server_number(ip):
    a, b, c, d = ip.split('.')
    a = int(a)
    b = int(b)
    c = int(c)
    d = int(d)
    return struct.unpack('i', struct.pack('I', 
        a | (b << 8) | (c << 16) | (d << 24)))[0]

def get_server_ip(number):
    try:
        if number.startswith('aos://'):
            number = number[6:]
            number = int(number)
    except AttributeError:
        pass
    a = number & 0xFF
    b = (number & 0xFF00) >> 8
    c = (number & 0xFF0000) >> 16
    d = (number & 0xFF000000) >> 24
    return '%s.%s.%s.%s' % (a, b, c, d)