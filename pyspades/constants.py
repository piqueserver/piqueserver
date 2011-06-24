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

HIT_VALUES = {
    2 : 100,
    1 : 40,
    3 : 25
}

HIT_CONSTANTS = dict([(v, k) for (k, v) in HIT_VALUES.iteritems()])

BUILD_BLOCK, DESTROY_BLOCK, SPADE_DESTROY, GRENADE_DESTROY = xrange(4)
MOVE_BLUE_FLAG, MOVE_GREEN_FLAG, MOVE_BLUE_BASE, MOVE_GREEN_BASE = xrange(4)

MAX_CHAT_SIZE = 90 # more like 95, but just to make sure

# strict values
# MAX_WALK_SPEED = 8
# MAX_FALL_SPEED = -32
# MAX_CLIMB_SPEED = 5

# sane values
MAX_WALK_SPEED = 16
MAX_FALL_SPEED = -40
MAX_CLIMB_SPEED = 8

MAX_TIMER_SPEED = 1700
TIMER_WINDOW_ENTRIES = 25