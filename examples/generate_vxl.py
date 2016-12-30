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

from pyspades.vxl import VXLData

map = VXLData()

for x in xrange(50, 512 - 50):
    for y in xrange(50, 512 - 50):
        for z in xrange(20, 58):
            map.set_point(x, y, z, (20, 20, 30, 40))

for x in range(512):
    for y in xrange(512):
        map.set_point(x, y, 62, (20, 20, 30, 40))
        map.set_point(x, y, 63, (20, 20, 30, 40))

for z in range(5, 64):
    map.set_point(256, 256, z, (20, 20, 30, 40))

print 'generating'

open('worldstick.vxl', 'wb').write(map.generate())
