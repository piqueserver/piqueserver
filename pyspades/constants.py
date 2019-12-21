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
RIFLE_WEAPON, SMG_WEAPON, SHOTGUN_WEAPON = range(3)
TORSO, HEAD, ARMS, LEGS, MELEE = range(5)
SPADE_TOOL, BLOCK_TOOL, WEAPON_TOOL, GRENADE_TOOL = range(4)
# BUILD_BLOCK: place a single block
# DESTROY_BLOCK: destroy a single block
# SPADE_DESTROY: destroy the block as well as the blocks directly above and
#   below it (spade right-click)
# GRENADE_DESTROY: destroy a 3x3 area around the block
BUILD_BLOCK, DESTROY_BLOCK, SPADE_DESTROY, GRENADE_DESTROY = range(4)
BLUE_FLAG, GREEN_FLAG, BLUE_BASE, GREEN_BASE = range(4)
CHAT_ALL, CHAT_TEAM, CHAT_SYSTEM = range(3)
(WEAPON_KILL, HEADSHOT_KILL, MELEE_KILL, GRENADE_KILL, FALL_KILL,
    TEAM_CHANGE_KILL, CLASS_CHANGE_KILL) = range(7)
(ERROR_UNDEFINED, ERROR_BANNED, ERROR_TOO_MANY_CONNECTIONS, ERROR_WRONG_VERSION,
    ERROR_FULL, ERROR_SHUTDOWN) = range(6)
ERROR_KICKED, ERROR_INVALID_NAME = 10, 20

CTF_MODE, TC_MODE = range(2)
TC_CAPTURE_DISTANCE = 16  # 16 blocks
TC_CAPTURE_RATE = 0.05
MIN_TERRITORY_COUNT = 3
MAX_TERRITORY_COUNT = 7
NEUTRAL_TEAM = 2
SPAWN_RADIUS = 32
MINE_RANGE = 3
BUILD_TOLERANCE = 5

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

# Game version IDs.
#
(
    GAME_VERSION_AOS_075,
    GAME_VERSION_AOS_076RC10,

    GAME_VERSION_COUNT,
) = range(2+1)

# Mapping of game versions to protocol versions.
#
# AoS since version 0.75 has used an increasing single-integer
# protocol version number.
#
# AoS 0.70 and older use a CRC-32 of the client.exe binary.
#
# Some prerelease versions of 0.75:
# - 0o075001: Not known. Possibly a test candidate version.
#             Yes, that's an octal number.
# - 1: 0.75RC12 and some older versions.
# - 2: Some later release candidate.
#
# 0.76 seems to have stuck with version 4 as it was never
# officially released as the mainline version.
#
GAME_PROTOCOL_VERSIONS = {
    GAME_VERSION_AOS_075: 3,
    GAME_VERSION_AOS_076RC10: 4,
}

GAME_VERSION_FROM_STRING = {
    "0.75": GAME_VERSION_AOS_075,
    "0.76": GAME_VERSION_AOS_076RC10,
}

GAME_VERSION_TO_STRING = {v: k for k, v in GAME_VERSION_FROM_STRING.items()}
