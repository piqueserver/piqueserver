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
pyspades - default/featured server
"""

import sys
import os
import json
import itertools
import random
import time
import shutil
from collections import deque

import argparse

import cfg

arg_parser = argparse.ArgumentParser(prog=cfg.pkg_name,
                                     description='%s is an open-source Python server implementation for the voxel-based game "Ace of Spades".' % cfg.pkg_name)

arg_parser.add_argument("-c","--config-file", default="config.json", 
        help="specify alternate config file (relative to config dir if relative path)")
arg_parser.add_argument("-j","--json-parameters", 
        help="add extra json parameters, overwriting that in config file")
arg_parser.add_argument("-d","--config-dir", default=cfg.config_dir,
        help="the directory which contains maps, scripts, etc (in correctly named subdirs) - default is %s" % cfg.config_path)

args = arg_parser.parse_args()


def choose_path(base,top):
    "helper function to choose the right path/file for the config, etc."
    if not os.path.isabs(top):
        return os.path.join(base,top)
    return top

# ok, so we use the resource directory to search for maps, etc.
config_dir = args.config_dir
cfg.config_dir = config_dir

# add it to the path so we can import scripts
sys.path.append(config_dir)
# add our package to path too so scripts can import `feauture_server/`
sys.path.insert(1, os.path.dirname(os.path.abspath(__file__))) # a better way instead of abs path?



# fix the path for the config file - handles differering directories and relative or absolute paths
config_file = choose_path(config_dir,args.config_file)
cfg.config_file = config_file

# default passwords hardcoded in config
DEFAULT_PASSWORDS = {
    'admin' : ['adminpass1', 'adminpass2', 'adminpass3'],
    'moderator' : ['modpass'],
    'guard' : ['guardpass'],
    'trusted' : ['trustedpass']
}

try:
    with open(config_file, 'rb') as f:
        config = json.load(f)
        cfg.config = config
except IOError as e:
    print("Error reading config from {}: ".format(config_file) + str(e))
    sys.exit(1)
except ValueError as e:
    print("Error in config file {}: ".format(config_file) + str(e))
    sys.exit(1)


# update with parameters from args
if args.json_parameters:
    json_parameter = args.json_parameters
    config.update(eval(json_parameter))


profile = config.get('profile', False)

frozen = hasattr(sys, 'frozen')

def get_git_rev():
    if not os.path.exists(".git"):
        return 'snapshot'

    from distutils.spawn import find_executable
    if find_executable("git") is None:
        return 'gitless'

    import subprocess
    pipe = subprocess.Popen(
        ["git", "rev-parse", "HEAD"],
        stdout=subprocess.PIPE, stderr = subprocess.PIPE)
    ret = pipe.stdout.read()[:40]
    if not ret:
        return 'unknown'
    return ret

if frozen:
    path = os.path.dirname(unicode(sys.executable, sys.getfilesystemencoding()))
    sys.path.append(path)
    try:
        SERVER_VERSION = 'win32 bin - rev %s' % (open('version', 'rb').read())
    except IOError:
        SERVER_VERSION = 'win32 bin'
else:
    sys.path.append('..')
    SERVER_VERSION = '%s - rev %s' % (sys.platform, get_git_rev())

if sys.platform == 'linux2':
    try:
        from twisted.internet import epollreactor
        epollreactor.install()
    except ImportError:
        print '(dependencies missing for epoll, using normal reactor)'

if sys.version_info < (2, 7):
    try:
        import psyco
        psyco.full()
    except ImportError:
        print '(optional: install psyco for optimizations)'

import pyspades.debug
from pyspades.server import (ServerProtocol, ServerConnection, position_data,
    grenade_packet, Team)
from map import Map, MapNotFound, check_rotation
from console import create_console
from twisted.internet import reactor
from twisted.internet.task import LoopingCall
from twisted.python import log
from twisted.python.logfile import DailyLogFile
from pyspades.web import getPage
from pyspades.common import encode, decode, prettify_timespan
from pyspades.constants import *
from pyspades.master import MAX_SERVER_NAME_SIZE, get_external_ip
from pyspades.tools import make_server_identifier
from pyspades.types import AttributeSet
from networkdict import NetworkDict, get_network
from pyspades.exceptions import InvalidData
from pyspades.bytes import NoDataLeft
from scheduler import Scheduler
import commands

def create_path(path):
    if path:
        try:
            os.makedirs(path)
        except OSError:
            pass

def create_filename_path(path):
    create_path(os.path.dirname(path))

def open_create(filename, mode):
    create_filename_path(filename)
    return open(filename, mode)

CHAT_WINDOW_SIZE = 5
CHAT_PER_SECOND = 0.5

class FeatureConnection(ServerConnection):
    printable_name = None
    admin = False
    last_switch = None
    mute = False
    deaf = False
    login_retries = None
    god = False
    god_build = False
    fly = False
    invisible = False
    building = True
    killing = True
    streak = 0
    best_streak = 0
    last_chat = None
    chat_time = 0
    chat_count = 0
    user_types = None

    def on_connect(self):
        protocol = self.protocol
        client_ip = self.address[0]
        try:
            name, reason, timestamp = self.protocol.bans[client_ip]
            if timestamp is not None and reactor.seconds() >= timestamp:
                protocol.remove_ban(client_ip)
                protocol.save_bans()
            else:
                print 'banned user %s (%s) attempted to join' % (name,
                    client_ip)
                self.disconnect(ERROR_BANNED)
                return
        except KeyError:
            pass
        manager = self.protocol.ban_manager
        if manager is not None:
            reason = manager.get_ban(client_ip)
            if reason is not None:
                print ('federated banned user (%s) attempted to join, '
                    'banned for %r') % (client_ip, reason)
                self.disconnect(ERROR_BANNED)
                return
        ServerConnection.on_connect(self)

    def on_join(self):
        if self.protocol.motd is not None:
            self.send_lines(self.protocol.motd)

    def on_login(self, name):
        self.printable_name = name.encode('ascii', 'replace')
        print '%s (IP %s, ID %s) entered the game!' % (self.printable_name,
            self.address[0], self.player_id)
        self.protocol.irc_say('* %s (IP %s, ID %s) entered the game!' %
            (self.name, self.address[0], self.player_id))
        if self.user_types is None:
            self.user_types = AttributeSet()
            self.rights = AttributeSet()
            if self.protocol.everyone_is_admin:
                self.on_user_login('admin', False)

    def get_spawn_location(self):
        get_location = self.protocol.map_info.get_spawn_location
        if get_location is not None:
            result = get_location(self)
            if result is not None:
                return result
        return ServerConnection.get_spawn_location(self)

    def on_disconnect(self):
        if self.name is not None:
            print self.printable_name, 'disconnected!'
            self.protocol.irc_say('* %s (IP %s) disconnected' %
                (self.name, self.address[0]))
            self.protocol.player_memory.append((self.name, self.address[0]))
        else:
            print '%s disconnected' % self.address[0]
        ServerConnection.on_disconnect(self)

    def on_command(self, command, parameters):
        result = commands.handle_command(self, command, parameters)
        if result == False:
            parameters = ['***'] * len(parameters)
        log_message = '<%s> /%s %s' % (self.name, command,
            ' '.join(parameters))
        if result:
            log_message += ' -> %s' % result
            self.send_chat(result)
        print log_message.encode('ascii', 'replace')

    def _can_build(self):
        if not self.building:
            return False
        if not self.god and not self.protocol.building:
            return False

    def on_block_build_attempt(self, x, y, z):
        return self._can_build()

    def on_line_build_attempt(self, points):
        return self._can_build()

    def on_line_build(self, points):
        if self.god:
            self.refill()
        if self.god_build:
            if self.protocol.god_blocks is None:
                self.protocol.god_blocks = set()
            self.protocol.god_blocks.update(points)
        elif self.protocol.user_blocks is not None:
            self.protocol.user_blocks.update(points)

    def on_block_build(self, x, y, z):
        if self.god:
            self.refill()
        if self.god_build:
            if self.protocol.god_blocks is None:
                self.protocol.god_blocks = set()
            self.protocol.god_blocks.add((x, y, z))
        elif self.protocol.user_blocks is not None:
            self.protocol.user_blocks.add((x, y, z))

    def on_block_destroy(self, x, y, z, mode):
        map_on_block_destroy = self.protocol.map_info.on_block_destroy
        if map_on_block_destroy is not None:
            result = map_on_block_destroy(self, x, y, z, mode)
            if result == False:
                return result
        if not self.building:
            return False
        if not self.god:
            if not self.protocol.building:
                return False
            is_indestructable = self.protocol.is_indestructable
            if mode == DESTROY_BLOCK:
                if is_indestructable(x, y, z):
                    return False
            elif mode == SPADE_DESTROY:
                if (is_indestructable(x, y, z) or
                is_indestructable(x, y, z + 1) or
                is_indestructable(x, y, z - 1)):
                    return False
            elif mode == GRENADE_DESTROY:
                for nade_x in xrange(x - 1, x + 2):
                    for nade_y in xrange(y - 1, y + 2):
                        for nade_z in xrange(z - 1, z + 2):
                            if is_indestructable(nade_x, nade_y, nade_z):
                                return False

    def on_block_removed(self, x, y, z):
        if self.protocol.user_blocks is not None:
            self.protocol.user_blocks.discard((x, y, z))
        if self.protocol.god_blocks is not None:
            self.protocol.god_blocks.discard((x, y, z))

    def on_hit(self, hit_amount, player, type, grenade):
        if not self.protocol.killing:
            self.send_chat(
                "You can't kill anyone right now! Damage is turned OFF")
            return False
        if not self.killing:
            self.send_chat("%s. You can't kill anyone." % player.name)
            return False
        elif player.god:
            if not player.invisible:
                self.send_chat("You can't hurt %s! That player is in "
                    "*god mode*" % player.name)
            return False
        if self.god:
            self.protocol.send_chat('%s, killing in god mode is forbidden!' %
                self.name, irc = True)
            self.protocol.send_chat('%s returned to being a mere human.' %
                self.name, irc = True)
            self.god = False
            self.god_build = False

    def on_kill(self, killer, type, grenade):
        self.streak = 0
        if killer is None or self.team is killer.team:
            return
        if not grenade or grenade.name == 'grenade':
            # doesn't give streak kills on airstrikes (or other types of
            # explosions)
            killer.streak += 1
            killer.best_streak = max(killer.streak, killer.best_streak)
        killer.team.kills += 1

    def on_reset(self):
        self.streak = 0
        self.best_streak = 0

    def on_animation_update(self, jump, crouch, sneak, sprint):
        if self.fly and crouch and self.world_object.velocity.z != 0.0:
            jump = True
        return jump, crouch, sneak, sprint

    def on_fall(self, damage):
        if self.god:
            return False
        if not self.protocol.fall_damage:
            return False

    def on_grenade(self, time_left):
        if self.god:
            self.refill()

    def on_team_join(self, team):
        if self.team is not None:
            if self.protocol.teamswitch_interval:
                teamswitch_interval = self.protocol.teamswitch_interval
                if teamswitch_interval == 'never':
                    self.send_chat('Switching teams is not allowed')
                    return False
                if (self.last_switch is not None and
                    reactor.seconds() - self.last_switch < teamswitch_interval * 60):
                    self.send_chat('You must wait before switching teams again')
                    return False
        if team.locked:
            self.send_chat('Team is locked')
            return False
        balanced_teams = self.protocol.balanced_teams
        if balanced_teams and not team.spectator:
            other_team = team.other
            if other_team.count() < team.count() + 1 - balanced_teams:
                self.send_chat('Team is full')
                return False
        self.last_switch = reactor.seconds()

    def on_chat(self, value, global_message):
        if not self.mute:
            current_time = reactor.seconds()
            if self.last_chat is None:
                self.last_chat = current_time
            else:
                self.chat_time += current_time - self.last_chat
                if self.chat_count > CHAT_WINDOW_SIZE:
                    if self.chat_count / self.chat_time > CHAT_PER_SECOND:
                        self.mute = True
                        self.protocol.send_chat(
                            '%s has been muted for excessive spam' % (self.name),
                            irc = True)
                    self.chat_time = self.chat_count = 0
                else:
                    self.chat_count += 1
                self.last_chat = current_time
        message = '<%s> %s' % (self.name, value)
        if self.mute:
            message = '(MUTED) %s' % message
        elif global_message and self.protocol.global_chat:
            self.protocol.irc_say('<%s> %s' % (self.name, value))
        print message.encode('ascii', 'replace')
        if self.mute:
            self.send_chat('(Chat not sent - you are muted)')
            return False
        elif global_message and not self.protocol.global_chat:
            self.send_chat('(Chat not sent - global chat disabled)')
            return False
        return value

    def kick(self, reason = None, silent = False):
        if not silent:
            if reason is not None:
                message = '%s was kicked: %s' % (self.name, reason)
            else:
                message = '%s was kicked' % self.name
            self.protocol.send_chat(message, irc = True)
        # FIXME: Client should handle disconnect events the same way in both
        # main and initial loading network loops
        self.disconnect(ERROR_KICKED + 8)

    def ban(self, reason = None, duration = None):
        reason = ': ' + reason if reason is not None else ''
        duration = duration or None
        if duration is None:
            message = '%s permabanned%s' % (self.name, reason)
        else:
            message = '%s banned for %s%s' % (self.name,
                prettify_timespan(duration * 60), reason)
        if self.protocol.on_ban_attempt(self, reason, duration):
            self.protocol.send_chat(message, irc = True)
            self.protocol.on_ban(self, reason, duration)
            if self.address[0]=="127.0.0.1":
                self.protocol.send_chat("Ban ignored: localhost")
            else:
                self.protocol.add_ban(self.address[0], reason, duration,
                                      self.name)

    def send_lines(self, lines):
        current_time = 0
        for line in lines:
            reactor.callLater(current_time, self.send_chat, line)
            current_time += 2

    def on_hack_attempt(self, reason):
        print 'Hack attempt detected from %s: %s' % (self.printable_name,
            reason)
        self.kick(reason)

    def on_user_login(self, user_type, verbose = True):
        if user_type == 'admin':
            self.admin = True
            self.speedhack_detect = False
        self.user_types.add(user_type)
        rights = set(commands.rights.get(user_type, ()))
        self.rights.update(rights)
        if verbose:
            message = ' logged in as %s' % (user_type)
            self.send_chat('You' + message)
            self.protocol.irc_say("* " + self.name + message)

    def timed_out(self):
        if self.name is not None:
            print '%s timed out' % self.printable_name
        ServerConnection.timed_out(self)

def encode_lines(value):
    if value is not None:
        lines = []
        for line in value:
            lines.append(encode(line))
        return lines

def random_choice_cycle(choices):
    while 1:
        yield random.choice(choices)

class FeatureTeam(Team):
    locked = False

    def get_entity_location(self, entity_id):
        get_location = self.protocol.map_info.get_entity_location
        if get_location is not None:
            result = get_location(self, entity_id)
            if result is not None:
                return result
        return Team.get_entity_location(self, entity_id)

class EndCall(object):
    active = True
    def __init__(self, protocol, delay, func, *arg, **kw):
        self.protocol = protocol
        protocol.end_calls.append(self)
        self.delay = delay
        self.func = func
        self.arg = arg
        self.kw = kw
        self.call = None

    def set(self, value):
        if value is None:
            if self.call is not None:
                self.call.cancel()
                self.call = None
        elif value is not None:
            value = value - self.delay
            if value <= 0.0:
                self.cancel()
            elif self.call:
                self.call.reset(value)
            else:
                self.call = reactor.callLater(value, self.fire)

    def fire(self):
        self.call = None
        self.cancel()
        self.func(*self.arg, **self.kw)

    def cancel(self):
        self.set(None)
        self.protocol.end_calls.remove(self)
        self.active = False

    def active(self):
        return self.active and (self.call and self.call.active())

class FeatureProtocol(ServerProtocol):
    connection_class = FeatureConnection
    bans = None
    ban_publish = None
    ban_manager = None
    everyone_is_admin = False
    player_memory = None
    irc_relay = None
    balanced_teams = None
    timestamps = None
    building = True
    killing = True
    global_chat = True
    remote_console = None
    debug_log = None
    advance_call = None
    master_reconnect_call = None
    master = False
    ip = None
    identifier = None

    planned_map = None

    map_info = None
    spawns = None
    user_blocks = None
    god_blocks = None

    last_time = None
    interface = None

    team_class = FeatureTeam

    game_mode = None # default to None so we can check
    time_announce_schedule = None

    server_version = SERVER_VERSION

    def __init__(self, interface, config):
        self.config = config
        if config.get('random_rotation', False):
            self.map_rotator_type = random_choice_cycle
        else:
            self.map_rotator_type = itertools.cycle
        self.default_time_limit = config.get('default_time_limit', 20.0)
        self.default_cap_limit = config.get('cap_limit', 10.0)
        self.advance_on_win = int(config.get('advance_on_win', False))
        self.win_count = itertools.count(1)
        self.bans = NetworkDict()
        try:
            self.bans.read_list(json.load(open(os.path.join(config_dir,'bans.txt'), 'rb')))
        except IOError:
            pass
        self.hard_bans = set() # possible DDoS'ers are added here
        self.player_memory = deque(maxlen = 100)
        self.config = config
        if len(self.name) > MAX_SERVER_NAME_SIZE:
            print '(server name too long; it will be truncated to "%s")' % (
                self.name[:MAX_SERVER_NAME_SIZE])
        self.respawn_time = config.get('respawn_time', 8)
        self.respawn_waves = config.get('respawn_waves', False)
        game_mode = config.get('game_mode', 'ctf')
        if game_mode == 'ctf':
            self.game_mode = CTF_MODE
        elif game_mode == 'tc':
            self.game_mode = TC_MODE
        elif self.game_mode is None:
            raise NotImplementedError('invalid game mode: %s' % game_mode)
        self.game_mode_name = game_mode
        team1 = config.get('team1', {})
        team2 = config.get('team2', {})
        self.team1_name = team1.get('name', 'Blue')
        self.team2_name = team2.get('name', 'Green')
        self.team1_color = tuple(team1.get('color', (0, 0, 196)))
        self.team2_color = tuple(team2.get('color', (0, 196, 0)))
        self.friendly_fire = config.get('friendly_fire', True)
        self.friendly_fire_time = config.get('grief_friendly_fire_time', 2.0)
        self.spade_teamkills_on_grief = config.get('spade_teamkills_on_grief',
            False)
        self.fall_damage = config.get('fall_damage', True)
        self.teamswitch_interval = config.get('teamswitch_interval', 0)
        self.max_players = config.get('max_players', 20)
        self.melee_damage = config.get('melee_damage', 100)
        self.max_connections_per_ip = config.get('max_connections_per_ip', 0)
        self.passwords = config.get('passwords', {})
        self.server_prefix = encode(config.get('server_prefix', '[*]'))
        self.time_announcements = config.get('time_announcements',
            [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 30, 60, 120, 180, 240, 300, 600,
             900, 1200, 1800, 2400, 3000])
        self.balanced_teams = config.get('balanced_teams', None)
        self.login_retries = config.get('login_retries', 1)

        # voting configuration
        self.default_ban_time = config.get('default_ban_duration', 24*60)

        self.speedhack_detect = config.get('speedhack_detect', True)
        if config.get('user_blocks_only', False):
            self.user_blocks = set()
        self.set_god_build = config.get('set_god_build', False)
        self.debug_log = config.get('debug_log', False)
        if self.debug_log:
            pyspades.debug.open_debug_log(os.path.join(config_dir,'debug.log'))
        ssh = config.get('ssh', {})
        if ssh.get('enabled', False):
            from ssh import RemoteConsole
            self.remote_console = RemoteConsole(self, ssh)
        irc = config.get('irc', {})
        if irc.get('enabled', False):
            from irc import IRCRelay
            self.irc_relay = IRCRelay(self, irc)
        status = config.get('status_server', {})
        if status.get('enabled', False):
            from statusserver import StatusServerFactory
            self.status_server = StatusServerFactory(self, status)
        publish = config.get('ban_publish', {})
        if publish.get('enabled', False):
            from banpublish import PublishServer
            self.ban_publish = PublishServer(self, publish)
        ban_subscribe = config.get('ban_subscribe', {})
        if ban_subscribe.get('enabled', True):
            import bansubscribe
            self.ban_manager = bansubscribe.BanManager(self, ban_subscribe)
        # logfile location in resource dir if not abs path given
        logfile = choose_path(config_dir,config.get('logfile', ''))
        if logfile.strip(): # catches empty filename 
            if config.get('rotate_daily', False):
                create_filename_path(logfile)
                logging_file = DailyLogFile(logfile, '.')
            else:
                logging_file = open_create(logfile, 'a')
            log.addObserver(log.FileLogObserver(logging_file).emit)
            log.msg('pyspades server started on %s' % time.strftime('%c'))
        log.startLogging(sys.stdout) # force twisted logging

        self.start_time = reactor.seconds()
        self.end_calls = []
        self.console = create_console(self)

        # check for default password usage
        for group, passwords in self.passwords.iteritems():
            if group in DEFAULT_PASSWORDS:
                for password in passwords:
                    if password in DEFAULT_PASSWORDS[group]:
                        print ("WARNING: FOUND DEFAULT PASSWORD '%s'" \
                               " IN GROUP '%s'" % (password, group))

        for password in self.passwords.get('admin', []):
            if not password:
                self.everyone_is_admin = True
        commands.rights.update(config.get('rights', {}))

        port = self.port = config.get('port', 32887)
        ServerProtocol.__init__(self, port, interface)
        self.host.intercept = self.receive_callback
        ret = self.set_map_rotation(config['maps'])
        if not ret:
            print 'Invalid map in map rotation (%s), exiting.' % ret.map
            raise SystemExit

        self.update_format()
        self.tip_frequency = config.get('tip_frequency', 0)
        if self.tips is not None and self.tip_frequency > 0:
            reactor.callLater(self.tip_frequency * 60, self.send_tip)

        self.master = config.get('master', True)
        self.set_master()

        get_external_ip(config.get('network_interface', '')).addCallback(
            self.got_external_ip)

    def got_external_ip(self, ip):
        self.ip = ip
        self.identifier = make_server_identifier(ip, self.port)
        print 'Server identifier is %s' % self.identifier

    def set_time_limit(self, time_limit = None, additive = False):
        advance_call = self.advance_call
        add_time = 0.0
        if advance_call is not None:
            add_time = ((advance_call.getTime() - reactor.seconds()) / 60.0)
            advance_call.cancel()
            self.advance_call = None
        time_limit = time_limit or self.default_time_limit
        if time_limit == False:
            for call in self.end_calls[:]:
                call.set(None)
            return

        if additive:
            time_limit = min(time_limit + add_time, self.default_time_limit)

        seconds = time_limit * 60.0
        self.advance_call = reactor.callLater(seconds, self._time_up)

        for call in self.end_calls[:]:
            call.set(seconds)

        if self.time_announce_schedule is not None:
            self.time_announce_schedule.reset()
        self.time_announce_schedule = Scheduler(self)
        for seconds in self.time_announcements:
            self.time_announce_schedule.call_end(seconds,
                self._next_time_announce)

        return time_limit

    def _next_time_announce(self):
        remaining = self.advance_call.getTime() - reactor.seconds()
        if remaining < 60.001:
            if remaining < 10.001:
                self.send_chat('%s...' % int(round(remaining)))
            else:
                self.send_chat('%s seconds remaining.' % int(round(remaining)))
        else:
            self.send_chat('%s minutes remaining.' % int(round(remaining/60)))

    def _time_up(self):
        self.advance_call = None
        self.advance_rotation('Time up!')

    def advance_rotation(self, message = None):
        self.set_time_limit(False)
        if self.planned_map is None:
            self.planned_map = self.map_rotator.next()
        map = self.planned_map
        self.planned_map = None
        self.on_advance(map)
        if message is None:
            self.set_map_name(map)
        else:
            self.send_chat('%s Next map: %s.' % (message, map.full_name),
                           irc = True)
            reactor.callLater(10, self.set_map_name, map)

    def get_mode_name(self):
        return self.game_mode_name

    def set_map_name(self, rot_info):
        try:
            map_info = self.get_map(rot_info)
        except MapNotFound, e:
            return e
        if self.map_info:
            self.on_map_leave()
        self.map_info = map_info
        self.max_score = self.map_info.cap_limit or self.default_cap_limit
        self.set_map(self.map_info.data)
        self.set_time_limit(self.map_info.time_limit)
        self.update_format()
        return True

    def get_map(self, rot_info):
        return Map(rot_info, os.path.join(config_dir,'maps'))
    
    def set_map_rotation(self, maps, now = True):
        try:
            maps = check_rotation(maps, os.path.join(config_dir,'maps'))
        except MapNotFound, e:
            return e
        self.maps = maps
        self.map_rotator = self.map_rotator_type(maps)
        if now:
            self.advance_rotation()
        return True

    def get_map_rotation(self):
        return [map.full_name for map in self.maps]

    def is_indestructable(self, x, y, z):
        if self.user_blocks is not None:
            if (x, y, z) not in self.user_blocks:
                return True
        if self.god_blocks is not None:
            if (x, y, z) in self.god_blocks:
                return True
        map_is_indestructable = self.map_info.is_indestructable
        if map_is_indestructable is not None:
            if map_is_indestructable(self, x, y, z) == True:
                return True
        return False

    def update_format(self):
        """
        Called when the map (or other variables) have been updated
        """
        config = self.config
        self.name = encode(self.format(config.get('name',
            'pyspades server %s' % random.randrange(0, 2000))))
        self.motd = self.format_lines(config.get('motd', None))
        self.help = self.format_lines(config.get('help', None))
        self.tips = self.format_lines(config.get('tips', None))
        self.rules = self.format_lines(config.get('rules', None))
        if self.master_connection is not None:
            self.master_connection.send_server()

    def format(self, value, extra = {}):
        map = self.map_info
        format_dict = {
            'map_name' : map.name,
            'map_author' : map.author,
            'map_description' : map.description,
            'game_mode' : self.get_mode_name()
        }
        format_dict.update(extra)
        return value % format_dict

    def format_lines(self, value):
        if value is None:
            return
        lines = []
        extra = {'server_name' : self.name}
        for line in value:
            lines.append(encode(self.format(line, extra)))
        return lines

    def got_master_connection(self, client):
        print 'Master connection established.'
        ServerProtocol.got_master_connection(self, client)

    def master_disconnected(self, client = None):
        ServerProtocol.master_disconnected(self, client)
        if self.master and self.master_reconnect_call is None:
            if client:
                message = 'Master connection could not be established'
            else:
                message = 'Master connection lost'
            print '%s, reconnecting in 60 seconds...' % message
            self.master_reconnect_call = reactor.callLater(60,
                self.reconnect_master)

    def reconnect_master(self):
        self.master_reconnect_call = None
        self.set_master()

    def set_master_state(self, value):
        if value == self.master:
            return
        self.master = value
        has_connection = self.master_connection is not None
        has_reconnect = self.master_reconnect_call is not None
        if value:
            if not has_connection and not has_reconnect:
                self.set_master()
        else:
            if has_reconnect:
                self.master_reconnect_call.cancel()
                self.master_reconnect_call = None
            if has_connection:
                self.master_connection.disconnect()

    def add_ban(self, ip, reason, duration, name = None):
        """
        Ban an ip with an optional reason and duration in minutes. If duration
        is None, ban is permanent.
        """
        network = get_network(ip)
        for connection in self.connections.values():
            if get_network(connection.address[0]) in network:
                name = connection.name
                connection.kick(silent = True)
        if duration:
            duration = reactor.seconds() + duration * 60
        else:
            duration = None
        self.bans[ip] = (name or '(unknown)', reason, duration)
        self.save_bans()

    def remove_ban(self, ip):
        results = self.bans.remove(ip)
        print 'Removing ban:', ip, results
        self.save_bans()

    def undo_last_ban(self):
        result = self.bans.pop()
        self.save_bans()
        return result

    def save_bans(self):
        json.dump(self.bans.make_list(), open_create(os.path.join(config_dir,'bans.txt'), 'wb'))
        if self.ban_publish is not None:
            self.ban_publish.update()

    def receive_callback(self, address, data):
        if data == 'HELLO':
            self.host.socket.send(address, 'HI')
            return 1
        if address.host in self.hard_bans:
            return 1

    def data_received(self, peer, packet):
        ip = peer.address.host
        current_time = reactor.seconds()
        try:
            ServerProtocol.data_received(self, peer, packet)
        except (NoDataLeft, InvalidData):
            import traceback
            traceback.print_exc()
            print 'IP %s was hardbanned for invalid data or possibly DDoS.' % ip
            self.hard_bans.add(ip)
            return
        dt = reactor.seconds() - current_time
        if dt > 1.0:
            print '(warning: processing %r from %s took %s)' % (
                packet.data, ip, dt)

    def irc_say(self, msg, me = False):
        if self.irc_relay:
            if me:
                self.irc_relay.me(msg, filter = True)
            else:
                self.irc_relay.send(msg, filter = True)

    def send_tip(self):
        line = self.tips[random.randrange(len(self.tips))]
        self.send_chat(line)
        reactor.callLater(self.tip_frequency * 60, self.send_tip)

    def send_chat(self, value, global_message = True, sender = None,
                  team = None, irc = False):
        if irc:
            self.irc_say('* %s' % value)
        ServerProtocol.send_chat(self, value, global_message, sender, team)

    # log high CPU usage

    def update_world(self):
        last_time = self.last_time
        current_time = reactor.seconds()
        if last_time is not None:
            dt = current_time - last_time
            if dt > 1.0:
                print '(warning: high CPU usage detected - %s)' % dt
        self.last_time = current_time
        ServerProtocol.update_world(self)
        time_taken = reactor.seconds() - current_time
        if time_taken > 1.0:
            print 'World update iteration took %s, objects: %s' % (time_taken,
                self.world.objects)

    # events

    def on_map_change(self, map):
        map_on_map_change = self.map_info.on_map_change
        if map_on_map_change is not None:
            map_on_map_change(self, map)

    def on_map_leave(self):
        map_on_map_leave = self.map_info.on_map_leave
        if map_on_map_leave is not None:
            map_on_map_leave(self)

    def on_game_end(self):
        if self.advance_on_win <= 0:
            self.irc_say('Round ended!', me = True)
        elif self.win_count.next() % self.advance_on_win == 0:
            self.advance_rotation('Game finished!')

    def on_advance(self, map_name):
        pass

    def on_ban_attempt(self, connection, reason, duration):
        return True

    def on_ban(self, connection, reason, duration):
        pass

    # voting

    def cancel_vote(self, connection = None):
        return 'No vote in progress.'

    # useful twisted wrappers

    def listenTCP(self, *arg, **kw):
        return reactor.listenTCP(*arg,
            interface = self.config.get('network_interface', ''), **kw)

    def connectTCP(self, *arg, **kw):
        return reactor.connectTCP(*arg,
            bindAddress = (self.config.get('network_interface', ''), 0), **kw)

    def getPage(self, *arg, **kw):
        return getPage(*arg,
            bindAddress = (self.config.get('network_interface', ''), 0), **kw)

    # before-end calls

    def call_end(self, delay, func, *arg, **kw):
        call = EndCall(self, delay, func, *arg, **kw)
        call.set(self.get_advance_time())
        return call

    def get_advance_time(self):
        if not self.advance_call:
            return None
        return self.advance_call.getTime() - self.advance_call.seconds()

PORT = 32887

# apply scripts

protocol_class = FeatureProtocol
connection_class = FeatureConnection

script_objects = []
script_names = config.get('scripts', [])
game_mode = config.get('game_mode', 'ctf')
if game_mode not in ('ctf', 'tc'):
    # must be a script with this game mode
    script_names.append(game_mode)


for script in script_names[:]:
    try:
        module = __import__('scripts.%s' % script, globals(), locals(),
            [script])
        script_objects.append(module)
    except ImportError, e:
        print "(script '%s' not found: %r)" % (script, e)
        script_names.remove(script)


for script in script_objects:
    protocol_class, connection_class = script.apply_script(protocol_class,
        connection_class, config)

protocol_class.connection_class = connection_class

interface = config.get('network_interface', '')
if interface == '':
    interface = '*'

protocol_instance = protocol_class(interface, config)
print 'Started server...'

if profile:
    import cProfile
    cProfile.run('reactor.run()', 'profile.dat')
else:
    reactor.run()
