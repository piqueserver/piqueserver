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
Collision-related 3D vector functions.
"""

import math
from typing import Any, Tuple


def vector_collision(vec1: Any, vec2: Any, distance: int = 3) -> bool:
    return (math.fabs(vec1.x - vec2.x) < distance and
            math.fabs(vec1.y - vec2.y) < distance and
            math.fabs(vec1.z - vec2.z) < distance)


def collision_3d(x1: float, y1: float, z1: float,
                 x2: float, y2: float, z2: float,
                 distance: int = 3) -> bool:
    return (math.fabs(x1 - x2) < distance and
            math.fabs(y1 - y2) < distance and
            math.fabs(z1 - z2) < distance)


def distance_3d_vector(vector1: Any, vector2: Any) -> float:
    xd = vector1.x - vector2.x # type: float
    yd = vector1.y - vector2.y # type: float
    zd = vector1.z - vector2.z # type: float
    return math.sqrt(xd**2 + yd**2 + zd**2)


def distance_3d(xyz1: Tuple[float, float, float],
                xyz2: Tuple[float, float, float]) -> float:
    (x1, y1, z1) = xyz1
    (x2, y2, z2) = xyz2
    xd = x1 - x2
    yd = y1 - y2
    zd = z1 - z2
    return math.sqrt(xd**2 + yd**2 + zd**2)
