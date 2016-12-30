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

import math

def vector_collision(vec1, vec2, distance = 3):
    return (math.fabs(vec1.x - vec2.x) < distance and
            math.fabs(vec1.y - vec2.y) < distance and
            math.fabs(vec1.z - vec2.z) < distance)

def collision_3d(x1, y1, z1, x2, y2, z2, distance = 3):
    return (math.fabs(x1 - x2) < distance and
            math.fabs(y1 - y2) < distance and
            math.fabs(z1 - z2) < distance)

def distance_3d_vector(vector1, vector2):
    xd = vector1.x - vector2.x
    yd = vector1.y - vector2.y
    zd = vector1.z - vector2.z
    return math.sqrt(xd**2 + yd**2 + zd**2)

def distance_3d((x1, y1, z1), (x2, y2, z2)):
    xd = x1 - x2
    yd = y1 - y2
    zd = z2 - z2
    return math.sqrt(xd**2 + yd**2 + zd**2)
