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

# FIXME: This should be probably moved into it's own URL thing and put into
# some module with a name describing it's insignificance

from ipaddress import IPv4Address
def make_server_identifier(ip: IPv4Address, port: int = 32887) -> str:
    # ip should be an IPv4Address object
    a, b, c, d = ip.exploded.split('.')
    a = int(a)
    b = int(b)
    c = int(c)
    d = int(d)
    return 'aos://{}:{}'.format(a | (b << 8) | (c << 16) | (d << 24), port)


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
    return ('{}.{}.{}.{}'.format(a, b, c, d), port)
