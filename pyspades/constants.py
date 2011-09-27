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

CONNECTIONLESS = 0xFFF

SEMI_WEAPON, SMG_WEAPON, SHOTGUN_WEAPON = xrange(3)

SPADE_TOOL, BLOCK_TOOL, WEAPON_TOOL, GRENADE_TOOL = xrange(4)

HIT_VALUES = {
    SEMI_WEAPON : {
        1 : 49,
        2 : 100,
        3 : 33
    },
    SMG_WEAPON : {
        1 : 24,
        2 : 75,
        3 : 16
    },
    SHOTGUN_WEAPON : {
        1 : 19,
        2 : 33,
        3 : 14
    }
}

BUILD_BLOCK, DESTROY_BLOCK, SPADE_DESTROY, GRENADE_DESTROY = xrange(4)
BLUE_FLAG, GREEN_FLAG, BLUE_BASE, GREEN_BASE = xrange(4)
(CHAT_UNKNOWN, CHAT_ALL, CHAT_TEAM, CHAT_SYSTEM) = xrange(4)
(WEAPON_KILL, GRENADE_KILL, FALL_KILL, TEAM_CHANGE_KILL, 
    CLASS_CHANGE_KILL) = xrange(5)

MAX_CHAT_SIZE = 90 # more like 95, but just to make sure

RUBBERBAND_DISTANCE = 3
RUBBERBAND_DISTANCE_Z = 2

MAX_TIMER_SPEED = 2000
TIMER_WINDOW_ENTRIES = 40
MAX_RAPID_SPEED = 60 # 1 minute
RAPID_WINDOW_ENTRIES = 10

UPDATE_FPS = 60.0
UPDATE_FREQUENCY = 1 / UPDATE_FPS

MIN_BLOCK_INTERVAL = 0.1

TOOL_INTERVAL = {
    SPADE_TOOL : 0.2,
    BLOCK_TOOL : 0.2,
    GRENADE_TOOL : 1.0
}

WEAPON_INTERVAL = {
    SEMI_WEAPON : 0.3,
    SMG_WEAPON : 0.1,
    SHOTGUN_WEAPON : 0.4
}