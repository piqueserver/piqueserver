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
Reads the AoSLang-En.bin file and allows you to manipulate it.
Thanks to learn_more for file format specs
"""

from pyspades.bytes import ByteReader, ByteWriter

MAGIC = 'STR0'

# for reference
FORMATS = [
    None,
    '',
    '%s',
    '%s %s',
    '%i',
    '%i %i %i',
    '%i %s',
    '%s %i',
    '%u'
]

class Entry(object):
    value = None
    type = None
    def __init__(self, value, type):
        self.value = value
        self.type = type

    def format(self, *arg):
        return self.value % arg

class LanguageFile(object):
    items = None
    def __init__(self, reader = None):
        self.items = []
        if reader is None:
            return
        if reader.read(4) != MAGIC:
            raise NotImplementedError('invalid magic')
        count = reader.readInt(True, False) - 1
        for _ in xrange(count):
            header = reader.readInt(True, False)
            end = reader.tell()
            off = header & 0x00FFFFFF
            type = header >> 24
            reader.seek(off)
            value = reader.readString()
            reader.seek(end)
            self.items.append(Entry(value, type))

    def write(self, reader):
        reader.write(MAGIC)
        size = len(self.items)
        start = 8 + size * 4
        reader.writeInt(size + 1, True, False)
        values = ByteWriter()
        for index, item in enumerate(self.items):
            value_offset = values.tell()
            values.writeString(item.value)
            offset = value_offset + start
            reader.writeInt(offset | (item.type << 24), True, False)
        reader.write(str(values))

    def generate(self):
        reader = ByteWriter()
        self.write(reader)
        return reader
