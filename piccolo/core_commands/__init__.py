# import everything here so at least we know commands will be registered
# also they are available to the rest of the code if required
from .game import get_time_limit, reset_game, lock, unlock, switch, set_balance, toggle_build, toggle_teamkill, global_chat, set_time_limit, fog
from .info import ping, rules, streak
from .map import mapname, show_rotation, change_planned_map, change_rotation, rotation_add, revert_rotation, advance
from .moderation import (get_ban_arguments, kick, ban, hban, dban, pban, banip,
                         unban, undo_ban, say, mute, unmute, ip, who_was,
                         invisible, godsilent, god, god_build)
from .movement import unstick, move_silent, move, where, teleport, tpsilent, fly
from .player import client, weapon, intel, kill, heal, deaf
from .server import server_name, server_info, version, scripts, toggle_master
from .social import login, pm, to_admin
