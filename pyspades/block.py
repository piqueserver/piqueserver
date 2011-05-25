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

from pyspades.astar import astar
from pyspades.collision import distance_3d

goal_pos = None
map = None

def neighbors((x, y, z)):
    return map.get_neighbors(x, y, z)

def goal(pos):
    return pos == goal_pos
    
def cost(a, b):
    return distance_3d(a, b)
    
def heuristic(pos):
    return distance_3d(pos, goal_pos)

def check_node(self, x, y, z):
    global goal_pos
    global map
    goal_pos = (x, y, self.get_height(x, y))
    start = (x, y, z)
    if start == goal_pos:
        return True
    map = self
    return astar((x, y, z), neighbors, goal, 0, cost, heuristic, 1000)