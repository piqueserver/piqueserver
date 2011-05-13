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

def binify(data, size = 2):
    binText = bin(data)[2:]
    binText = (2 * 8 - len(binText)) * '0' + binText
    return binText

MAX_HEX_SIZE = 110

def hexify(data, max = MAX_HEX_SIZE):
    hexed = data.encode('hex')
    if max is not None and len(hexed) > max:
        hexed = '%s (...)' % hexed[:max]
    return hexed

def stringify(data, max = MAX_HEX_SIZE):
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
        raise NotImplementedError('was %s, should be %s' % (value, default))