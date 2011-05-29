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

def get_color(color):
    b = color & 0xFF
    g = (color & 0xFF00) >> 8
    r = (color & 0xFF0000) >> 16
    return r, g, b

def make_color(r, g, b):
    return b | (g << 8) | (r << 16)

def binify(data, size = 2):
    binText = bin(str(data))[2:]
    binText = (2 * 8 - len(binText)) * '0' + binText
    return binText

MAX_HEX_SIZE = 110

def hexify(data, max = MAX_HEX_SIZE):
    hexed = str(data).encode('hex')
    if max is not None and len(hexed) > max:
        hexed = '%s (...)' % hexed[:max]
    return hexed

def stringify(data, max = MAX_HEX_SIZE):
    data = str(data)
    if max is not None and len(data) > max:
        data = '%s (...)' % data[:max]
    return '%r' % data

def compare_reader(reader, value, name):
    if reader.read(len(value)) != value:
        print '%s is wrong' % name

def open_debugger(name, locals):
    print '%s, opening debugger' % name
    import code
    code.interact(local = locals)

def check_default(value, default):
    if value != default:
        raw_input('check_default() failed')
        raise NotImplementedError('was %s, should be %s' % (value, default))

import zlib
def crc32(data):
    return zlib.crc32(data) & 0xffffffff

# Ace of Spades uses the CP437 character set

def encode(value):
    if value is not None:
        return value.encode('cp437')

def decode(value):
    if value is not None:
        return value.decode('cp437')