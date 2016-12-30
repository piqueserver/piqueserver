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

from pyspades.common import *

cdef class Loader:
    def __init__(self, ByteReader reader = None):
        if reader is not None:
            self.read(reader)

    cpdef read(self, ByteReader reader):
        read_python = getattr(self, 'read', None)
        if read_python is None:
            raise NotImplementedError('read() not implemented')
        read_python(reader)

    cpdef write(self, ByteWriter reader):
        write_python = getattr(self, 'write', None)
        if read_python is None:
            raise NotImplementedError('write() not implemented')
        write_python(reader)

    cpdef ByteWriter generate(self):
        cdef ByteWriter reader = ByteWriter()
        self.write(reader)
        return reader
