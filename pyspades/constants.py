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

MASTER_VERSION = 31
GAME_VERSION = 3

RIFLE_WEAPON = 0
SMG_WEAPON = 1
SHOTGUN_WEAPON = 2

TORSO = 0
HEAD = 1
ARMS = 2
LEGS = 3
MELEE = 4

SPADE_TOOL = 0
BLOCK_TOOL = 1
WEAPON_TOOL = 2
GRENADE_TOOL = 3

# place a single block
BUILD_BLOCK = 0
# destroy a single block
DESTROY_BLOCK = 1
# destroy the block as well as the blocks directly above and
# below it (spade right-click)
SPADE_DESTROY = 2
# destroy a 3x3 area around the block
GRENADE_DESTROY = 3

BLUE_FLAG = 0
GREEN_FLAG = 1
BLUE_BASE = 2
GREEN_BASE = 3

CHAT_ALL = 0
CHAT_TEAM = 1
CHAT_SYSTEM = 2
CHAT_BIG = 3
CHAT_INFO = 4
CHAT_WARNING = 5
CHAT_ERROR = 6

WEAPON_KILL = 0
HEADSHOT_KILL = 1
MELEE_KILL = 2
GRENADE_KILL = 3
FALL_KILL = 4
TEAM_CHANGE_KILL = 5
CLASS_CHANGE_KILL = 6

ERROR_UNDEFINED = 0
ERROR_BANNED = 1
ERROR_TOO_MANY_CONNECTIONS = 2
ERROR_WRONG_VERSION = 3
ERROR_FULL = 4
ERROR_SHUTDOWN = 5

ERROR_KICKED = 10
ERROR_INVALID_NAME = 20

EXTENSION_PLAYERLIMIT = 192
EXTENSION_CHATTYPE = 193
EXTENSION_KICKREASON = 194

EXTENSION_NAMES = {
    EXTENSION_PLAYERLIMIT: "player limit",
    EXTENSION_CHATTYPE: "chat type",
    EXTENSION_KICKREASON: "kick reason",
}

CTF_MODE = 0
TC_MODE = 1

TC_CAPTURE_DISTANCE = 16  # 16 blocks
TC_CAPTURE_RATE = 0.05
MIN_TERRITORY_COUNT = 3
MAX_TERRITORY_COUNT = 7
NEUTRAL_TEAM = 2
SPAWN_RADIUS = 32
MINE_RANGE = 3
BUILD_TOLERANCE = 5

FOG_DISTANCE = 128.0

MELEE_DISTANCE = 3

MAX_CHAT_SIZE = 90  # more like 95, but just to make sure

RUBBERBAND_DISTANCE = 3

MAX_TIMER_SPEED = 2000
TIMER_WINDOW_ENTRIES = 40
MAX_RAPID_SPEED = 60  # 1 minute
RAPID_WINDOW_ENTRIES = 10

POSITION_RATE = 1
MAX_POSITION_RATE = 0.7

UPDATE_FPS = 60.0
UPDATE_FREQUENCY = 1 / UPDATE_FPS
NETWORK_FPS = 10.0

MIN_BLOCK_INTERVAL = 0.1
MAX_BLOCK_DISTANCE = 6
MAX_DIG_DISTANCE = 6
HIT_TOLERANCE = 5.0
CLIP_TOLERANCE = 10

TOOL_INTERVAL = {
    SPADE_TOOL: 0.1,
    BLOCK_TOOL: 0.1,
    GRENADE_TOOL: 1.0
}

WEAPON_INTERVAL = {
    RIFLE_WEAPON: 0.2,
    SMG_WEAPON: 0.05,
    SHOTGUN_WEAPON: 0.3
}

OPENSPADES_CHATTYPES = {
    CHAT_BIG: "C% ",
    CHAT_INFO: "N% ",
    CHAT_WARNING: "%% ",
    CHAT_ERROR: "!% "
}
