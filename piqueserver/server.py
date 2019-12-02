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

# pylint: disable=too-many-lines
"""
pyspades - default/featured server
"""
import asyncio
import itertools
import json
import os
import random
import sys
import time
from collections import deque
from ipaddress import AddressValueError, IPv4Address, ip_address, ip_network
from pprint import pprint
from typing import Any, Callable, Dict, Iterator, List, Optional, Tuple

import aiohttp
from enet import Address, Packet, Peer
from twisted.internet import reactor, threads
from twisted.internet.defer import Deferred, ensureDeferred, inlineCallbacks
from twisted.internet.task import LoopingCall, coiterate, deferLater
from twisted.internet.tcp import Port
from twisted.logger import (FilteringLogObserver, Logger, LogLevel,
                            LogLevelFilterPredicate, globalLogBeginner,
                            textFileLogObserver)
from twisted.python.logfile import DailyLogFile

# won't be used; just need to be executed
import piqueserver.core_commands  # pylint: disable=unused-import
from piqueserver import commands, extensions
from piqueserver.config import cast_duration, config
from piqueserver.console import create_console
from piqueserver.map import Map, MapNotFound, RotationInfo, check_rotation
from piqueserver.networkdict import NetworkDict
from piqueserver.player import FeatureConnection
from piqueserver.release import check_for_releases, format_release
from piqueserver.scheduler import Scheduler
from piqueserver.utils import as_deferred
from piqueserver.bansubscribe import bans_config_urls
from pyspades.bytes import NoDataLeft
from pyspades.constants import CTF_MODE, ERROR_SHUTDOWN, TC_MODE
from pyspades.master import MAX_SERVER_NAME_SIZE
from pyspades.server import ServerProtocol, Team
from pyspades.tools import make_server_identifier
from pyspades.vxl import VXLData

log = Logger()


def validate_team_name(name):
    if len(name) > 9:
        log.warn(
            "Team name's length exceeds 9 character limit. More info: https://git.io/fN2cI")
        # TODO: Once issue #345 is sorted out, we can do a proper validation
        # for now we just warn
        # return False
    return True

# TODO: move to a better place if reusable


def sleep(secs):
    return deferLater(reactor, secs, lambda: None)


# declare configuration options
bans_config = config.section('bans')
logging_config = config.section('logging')
team1_config = config.section('team1')
team2_config = config.section('team2')

bans_file = bans_config.option('file', default='bans.txt')
bans_urls = bans_config.option('urls', [])
respawn_time_option = config.option(
    'respawn_time', default="8sec", cast=cast_duration)
respawn_waves = config.option('respawn_waves', default=False)
game_mode = config.option('game_mode', default='ctf')
random_rotation = config.option('random_rotation', default=False)
passwords = config.option('passwords', default={})
logfile = logging_config.option('logfile', default='./logs/log.txt')
loglevel = logging_config.option('loglevel', default='info')
map_rotation = config.option('rotation', default=['classicgen', 'random'],
                             validate=lambda x: isinstance(x, list))
default_time_limit = config.option(
    'default_time_limit', default="20min",
    cast=lambda x: cast_duration(x)/60)
cap_limit = config.option('cap_limit', default=10,
                          validate=lambda x: isinstance(x, (int, float)))
advance_on_win = config.option('advance_on_win', default=False,
                               validate=lambda x: isinstance(x, bool))
everyone_is_admin = config.option('everyone_is_admin', default=False,
                               validate=lambda x: isinstance(x, bool))
team1_name = team1_config.option(
    'name', default='Blue', validate=validate_team_name)
team2_name = team2_config.option(
    'name', default='Green', validate=validate_team_name)
team1_color = team1_config.option('color', default=(0, 0, 196))
team2_color = team2_config.option('color', default=(0, 196, 0))
friendly_fire = config.option('friendly_fire', default=False)
friendly_fire_on_grief = config.option('friendly_fire_on_grief',
                                       default=True)
grief_friendly_fire_time = config.option('grief_friendly_fire_time',
                                         default='2sec', cast=cast_duration)
spade_teamkills_on_grief = config.option('spade_teamkills_on_grief',
                                         default=False)
time_announcements = config.option('time_announcements', default=[1, 2, 3, 4, 5, 6, 7, 8, 9, 10,
                                                                  30, 60, 120, 180, 240, 300, 600,
                                                                  900, 1200, 1800, 2400, 3000])
rights = config.option('rights', default={})
port_option = config.option('port', default=32887,
                            validate=lambda n: isinstance(n, int))
fall_damage = config.option('fall_damage', default=True)
teamswitch_interval = config.option(
    'teamswitch_interval', default="0sec", cast=cast_duration)
teamswitch_allowed = config.option('teamswitch_allowed', default=True)
max_players = config.option('max_players', default=20)
melee_damage = config.option('melee_damage', default=100)
max_connections_per_ip = config.option('max_connections_per_ip', default=0)
server_prefix = config.option('server_prefix', default='[*]')
balanced_teams = config.option('balanced_teams', default=2)
login_retries = config.option('login_retries', 1)
default_ban_duration = bans_config.option(
    'default_duration', default="1day", cast=cast_duration)
speedhack_detect = config.option('speedhack_detect', True)
rubberband_distance = config.option('rubberband_distance', default=10)
user_blocks_only = config.option('user_blocks_only', False)
debug_log_enabled = logging_config.option('debug_log', False)
logging_profile_option = logging_config.option('profile', False)
set_god_build = config.option('set_god_build', False)
ssh_enabled = config.section('ssh').option('enabled', False)
irc_options = config.option('irc', {})
status_server_enabled = config.section(
    'status_server').option('enabled', False)
ban_publish = bans_config.option('publish', False)
ban_publish_port = bans_config.option('publish_port', 32885)
logging_rotate_daily = logging_config.option('rotate_daily', False)
tip_frequency = config.option(
    'tips_frequency', default="5sec", cast=lambda x: cast_duration(x)/60)
register_master_option = config.option('master', False)

default_ip_getter = 'https://services.buildandshoot.com/getip'
ip_getter_option = config.option('ip_getter', default_ip_getter)
name_option = config.option(
    'name', default='piqueserver #%s' % random.randrange(0, 2000))
motd_option = config.option('motd')
help_option = config.option('help', default=[
    'Server name: %(server_name)s',
    'Map: %(map_name)s by %(map_author)s',
    'Game mode: %(game_mode)s',
    '/commands Prints all available commands',
    '/help <command_name> Gives description and usage info for a command',
    '/help Prints this message',
])
rules_option = config.option('rules')
tips_option = config.option('tips')
network_interface = config.option('network_interface', default='')
scripts_option = config.option(
    'scripts', default=[], validate=extensions.check_scripts)


def ensure_dir_exists(filename: str) -> None:
    d = os.path.dirname(filename)
    os.makedirs(d, exist_ok=True)


def random_choice_cycle(choices):
    while True:
        yield random.choice(choices)


class FeatureTeam(Team):
    locked = False

    def get_entity_location(self, entity_id: int) -> Tuple[int, int, int]:
        get_location = self.protocol.map_info.get_entity_location
        if get_location is not None:
            result = get_location(self, entity_id)
            if result is not None:
                return result
        return Team.get_entity_location(self, entity_id)


class EndCall:
    _active = True

    def __init__(self, protocol, delay: int, func: Callable, *arg, **kw) -> None:
        self.protocol = protocol
        protocol.end_calls.append(self)
        self.delay = delay
        self.func = func
        self.arg = arg
        self.kw = kw
        self.call = None  # type: Deferred

    def set(self, value: Optional[float]) -> None:
        if value is None:
            if self.call is not None:
                self.call.cancel()
                self.call = None
        elif value is not None:
            value = value - self.delay
            if value <= 0.0:
                self.cancel()
            elif self.call:
                # In Twisted==18.9.0, reset() is broken when using
                # AsyncIOReactor
                # self.call.reset(value)
                self.call.cancel()
                self.call = reactor.callLater(value, self.fire)
            else:
                self.call = reactor.callLater(value, self.fire)

    def fire(self):
        self.call = None
        self.cancel()
        self.func(*self.arg, **self.kw)

    def cancel(self) -> None:
        self.set(None)
        self.protocol.end_calls.remove(self)
        self._active = False

    def active(self) -> bool:
        return self._active and (self.call and self.call.active())


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

    game_mode = None  # default to None so we can check
    time_announce_schedule = None

    default_fog = (128, 232, 255)

    def __init__(self, interface: bytes, config_dict: Dict[str, Any]) -> None:
        # logfile path relative to config dir if not abs path
        log_filename = logfile.get()
        if log_filename.strip():  # catches empty filename
            if not os.path.isabs(log_filename):
                log_filename = os.path.join(config.config_dir, log_filename)
            ensure_dir_exists(log_filename)
            if logging_rotate_daily.get():
                logging_file = DailyLogFile(log_filename, '.')
            else:
                logging_file = open(log_filename, 'a')
            predicate = LogLevelFilterPredicate(
                LogLevel.levelWithName(loglevel.get()))
            observers = [
                FilteringLogObserver(
                    textFileLogObserver(sys.stderr), [predicate]),
                FilteringLogObserver(
                    textFileLogObserver(logging_file), [predicate])
            ]
            globalLogBeginner.beginLoggingTo(observers)
            log.info('piqueserver started on %s' % time.strftime('%c'))

        self.config = config_dict
        if random_rotation.get():
            self.map_rotator_type = random_choice_cycle
        else:
            self.map_rotator_type = itertools.cycle
        self.default_time_limit = default_time_limit.get()
        self.default_cap_limit = cap_limit.get()
        self.advance_on_win = int(advance_on_win.get())
        self.win_count = itertools.count(1)
        self.bans = NetworkDict()

        # attempt to load a saved bans list
        try:
            with open(os.path.join(config.config_dir, bans_file.get()), 'r') as f:
                self.bans.read_list(json.load(f))
            log.debug("loaded {count} bans", count=len(self.bans))
        except FileNotFoundError:
            log.debug("skip loading bans: file unavailable",
                      count=len(self.bans))
        except IOError as e:
            log.error('Could not read bans file ({}): {}'.format(bans_file.get(), e))
        except ValueError as e:
            log.error('Could not parse bans file ({}): {}'.format(bans_file.get(), e))

        self.hard_bans = set()  # possible DDoS'ers are added here
        self.player_memory = deque(maxlen=100)
        if len(self.name) > MAX_SERVER_NAME_SIZE:
            log.warn('(server name too long; it will be truncated to "%s")' % (
                self.name[:MAX_SERVER_NAME_SIZE]))
        self.respawn_time = respawn_time_option.get()
        self.respawn_waves = respawn_waves.get()

        # since AoS only supports CTF and TC at a protocol level, we need to get
        # the base game mode if we are using a custom game mode.
        game_mode_name = game_mode.get()
        if game_mode_name == 'ctf':
            self.game_mode = CTF_MODE
        elif game_mode.get() == 'tc':
            self.game_mode = TC_MODE
        elif self.game_mode not in [CTF_MODE, TC_MODE]:
            raise ValueError(
                'invalid game mode: custom game mode "{}" does not set '
                'protocol.game_mode to one of TC_MODE or CTF_MODE. Are '
                'you sure the thing you have specified is a game mode?'.format(
                    game_mode_name))

        self.game_mode_name = game_mode.get().split('.')[-1]
        self.team1_name = team1_name.get()[:9]
        self.team2_name = team2_name.get()[:9]
        self.team1_color = tuple(team1_color.get())
        self.team2_color = tuple(team2_color.get())
        self.friendly_fire = friendly_fire.get()
        self.friendly_fire_on_grief = friendly_fire_on_grief.get()
        self.friendly_fire_time = grief_friendly_fire_time.get()
        self.spade_teamkills_on_grief = spade_teamkills_on_grief.get()
        self.fall_damage = fall_damage.get()
        self.teamswitch_interval = teamswitch_interval.get()
        self.teamswitch_allowed = teamswitch_allowed.get()
        self.max_players = max_players.get()
        self.melee_damage = melee_damage.get()
        self.max_connections_per_ip = max_connections_per_ip.get()
        self.passwords = passwords.get()
        self.server_prefix = server_prefix.get()
        self.time_announcements = time_announcements.get()
        self.balanced_teams = balanced_teams.get()
        self.login_retries = login_retries.get()

        # voting configuration
        self.default_ban_time = default_ban_duration.get()

        self.speedhack_detect = speedhack_detect.get()
        self.rubberband_distance = rubberband_distance.get()
        if user_blocks_only.get():
            self.user_blocks = set()
        self.set_god_build = set_god_build.get()
        self.debug_log = debug_log_enabled.get()
        if self.debug_log:
            # TODO: make this configurable
            pyspades.debug.open_debug_log(
                os.path.join(config.config_dir, 'debug.log'))
        if ssh_enabled.get():
            from piqueserver.ssh import RemoteConsole
            self.remote_console = RemoteConsole(self)
        irc = irc_options.get()
        if irc.get('enabled', False):
            from piqueserver.irc import IRCRelay
            self.irc_relay = IRCRelay(self, irc)
        if status_server_enabled.get():
            from piqueserver.statusserver import StatusServer
            self.status_server = StatusServer(self)
            ensureDeferred(self.status_server.listen())
        if ban_publish.get():
            from piqueserver.banpublish import PublishServer
            self.ban_publish = PublishServer(self, ban_publish_port.get())
        if bans_config_urls.get():
            from piqueserver import bansubscribe
            self.ban_manager = bansubscribe.BanManager(self)
        self.start_time = time.time()
        self.end_calls = []
        # TODO: why is this here?
        create_console(self)

        for user_type, func_names in rights.get().items():
            for func_name in func_names:
                commands.add_rights(user_type, func_name)

        if everyone_is_admin.get():
            self.everyone_is_admin = True

        self.port = port_option.get()
        ServerProtocol.__init__(self, self.port, interface)
        self.host.intercept = self.receive_callback

        try:
            self.set_map_rotation(self.config['rotation'])
        except MapNotFound as e:
            log.critical('Invalid map in map rotation (%s), exiting.' % e.map)
            raise SystemExit

        map_load_d = self.advance_rotation()
        # discard the result of the map advance for now
        map_load_d.addCallback(lambda x: self._post_init())

        ip_getter = ip_getter_option.get()
        if ip_getter:
            ensureDeferred(as_deferred(self.get_external_ip(ip_getter)))

        self.new_release = None
        notify_new_releases = config.option(
            "release_notifications", default=True)
        if notify_new_releases.get():
            ensureDeferred(as_deferred(self.watch_for_releases()))

        self.vacuum_loop = LoopingCall(self.vacuum_bans)
        # Run the vacuum every 6 hours, and kick it off it right now
        self.vacuum_loop.start(60 * 60 * 6, True)

        reactor.addSystemEventTrigger(
            'before', 'shutdown', lambda: ensureDeferred(self.shutdown()))

    def _post_init(self):
        """called after the map has been loaded"""
        self.update_format()
        self.tip_frequency = tip_frequency.get()
        if self.tips is not None and self.tip_frequency > 0:
            reactor.callLater(self.tip_frequency * 60, self.send_tip)

        self.master = register_master_option.get()
        self.set_master()

    async def get_external_ip(self, ip_getter: str) -> Iterator[Deferred]:
        log.info(
            'Retrieving external IP from {!r} to generate server identifier.'.format(ip_getter))
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(ip_getter) as response:
                    ip = await response.text()
                    ip = IPv4Address(ip.strip())
        except AddressValueError as e:
            log.warn('External IP getter service returned invalid data.\n'
                     'Please check the "ip_getter" setting in your config.')
            return
        except Exception as e:  # pylint: disable=broad-except
            log.warn("Getting external IP failed: {reason}", reason=e)
            return

        self.ip = ip
        self.identifier = make_server_identifier(ip, self.port)
        log.info('Server public ip address: {}:{}'.format(ip, self.port))
        log.info('Public aos identifier: {}'.format(self.identifier))

    def set_time_limit(self, time_limit: Optional[int] = None, additive:
                       bool = False) -> Optional[int]:
        advance_call = self.advance_call
        add_time = 0.0
        if advance_call is not None:
            add_time = ((advance_call.getTime() - reactor.seconds()) / 60.0)
            advance_call.cancel()
            self.advance_call = None
        time_limit = time_limit or self.default_time_limit
        if not time_limit:
            for call in self.end_calls[:]:
                call.set(None)
            return None

        if additive:
            time_limit = min(time_limit + add_time, self.default_time_limit)

        seconds = time_limit * 60
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
            self.send_chat('%s minutes remaining.' %
                           int(round(remaining / 60)))

    def _time_up(self):
        self.advance_call = None
        self.advance_rotation('Time up!')

    def advance_rotation(self, message: Optional[str] = None) -> Deferred:
        """
        Advances to the next map in the rotation. If message is provided
        it will send it to the chat, waits for 10 seconds and then advances.

        Returns:
            Deferred that fires when the map has been loaded
        """
        self.set_time_limit(False)
        if self.planned_map is None:
            self.planned_map = next(self.map_rotator)
        planned_map = self.planned_map
        self.planned_map = None
        self.on_advance(planned_map)

        async def do_advance():
            if message is not None:
                log.info("advancing to map '{name}' ({reason}) in 10 seconds",
                         name=planned_map.full_name, reason=message)
                self.send_chat(
                    '{} Next map: {}.'.format(message, planned_map.full_name),
                    irc=True)
                await sleep(10)
            else:
                log.info("advancing to map '{name}'",
                         name=planned_map.full_name)

            await self.set_map_name(planned_map)

        return ensureDeferred(do_advance())

    def get_mode_name(self) -> str:
        return self.game_mode_name

    async def set_map_name(self, rot_info: RotationInfo) -> None:
        """
        Sets the map by its name.
        """
        map_info = await self.make_map(rot_info)
        if self.map_info:
            self.on_map_leave()
        self.map_info = map_info
        self.max_score = self.map_info.cap_limit or self.default_cap_limit
        self.set_map(self.map_info.data)
        self.set_time_limit(self.map_info.time_limit)
        self.update_format()

    def set_server_name(self, name: str) -> None:
        name_option.set(name)
        self.update_format()

    def make_map(self, rot_info: RotationInfo) -> Deferred:
        """
        Creates and returns a Map object from rotation info in a new thread

        Returns:
            Deferred that resolves to a `Map` object.
        """
        # we must do this in a new thread, since map generation might take so
        # long that clients time out.
        return threads.deferToThread(
            Map, rot_info, os.path.join(config.config_dir, 'maps'))

    def set_map_rotation(self, maps: List[str]) -> None:
        """
        Over-writes the current map rotation with provided one.
        `FeatureProtocol.advance_rotation` still needs to be called to actually
        change the map,
        """
        maps = check_rotation(maps, os.path.join(config.config_dir, 'maps'))
        self.maps = maps
        self.map_rotator = self.map_rotator_type(maps)

    def get_map_rotation(self):
        return [map_item.full_name for map_item in self.maps]

    def is_indestructable(self, x: int, y: int, z: int) -> bool:
        if self.user_blocks is not None:
            if (x, y, z) not in self.user_blocks:
                return True
        if self.god_blocks is not None:
            if (x, y, z) in self.god_blocks:  # pylint: disable=unsupported-membership-test
                return True
        map_is_indestructable = self.map_info.is_indestructable
        if map_is_indestructable is not None:
            if map_is_indestructable(self, x, y, z):
                return True
        return False

    def update_format(self) -> None:
        """
        Called when the map (or other variables) have been updated
        """
        self.name = self.format(name_option.get())
        self.motd = self.format_lines(motd_option.get())
        self.help = self.format_lines(help_option.get())
        self.tips = self.format_lines(tips_option.get())
        self.rules = self.format_lines(rules_option.get())
        if self.master_connection is not None:
            self.master_connection.send_server()

    def format(self, value: str, extra: Optional[Dict[str, str]] = None) -> str:
        map_info = self.map_info
        format_dict = {
            'map_name': map_info.name,
            'map_author': map_info.author,
            'map_description': map_info.description,
            'game_mode': self.get_mode_name(),
            'server_name': self.name,
        }

        if extra:
            format_dict.update(extra)
        # format with both old-style and new string formatting to stay
        # compatible with older configs
        return value.format(**format_dict) % format_dict

    def format_lines(self, value: List[str]) -> List[str]:
        if value is None:
            return
        return [self.format(line) for line in value]

    def got_master_connection(self, client):
        log.info('Master connection established.')
        ServerProtocol.got_master_connection(self, client)

    def master_disconnected(self, client=None):
        ServerProtocol.master_disconnected(self, client)
        if self.master and self.master_reconnect_call is None:
            if client:
                message = 'Master connection could not be established'
            else:
                message = 'Master connection lost'
            log.info('%s, reconnecting in 60 seconds...' % message)
            self.master_reconnect_call = reactor.callLater(
                60, self.reconnect_master)

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

    async def shutdown(self):
        """
        Notifies players and disconnects them before a shutdown.
        """
        if not self.connections:
            # exit instantly if nobody is connected anyway
            return

        # send shutdown notification
        log.info("disconnecting players")
        self.broadcast_chat("Server shutting down in 3sec.")
        for i in range(3, 0, -1):
            self.broadcast_chat(str(i)+"...")
            await sleep(1)

        # disconnect all players
        for connection in list(self.connections.values()):
            connection.disconnect(ERROR_SHUTDOWN)

        # give the connections some time to terminate
        await sleep(0.2)

    def add_ban(self, ip, reason, duration, name=None):
        """
        Ban an ip with an optional reason and duration in seconds. If duration
        is None, ban is permanent.
        """
        network = ip_network(str(ip), strict=False)
        for connection in list(self.connections.values()):
            if ip_address(connection.address[0]) in network:
                name = connection.name
                connection.kick(silent=True)
        if duration:
            duration = reactor.seconds() + duration
        else:
            duration = None
        self.bans[ip] = (name or '(unknown)', reason, duration)
        self.save_bans()

    def remove_ban(self, ip):
        results = self.bans.remove(ip)
        log.info('Removing ban: {ip} {results}',
                 ip=ip, results=results)
        self.save_bans()

    async def watch_for_releases(self):
        """Starts a loop for `check_for_releases` and updates `self.new_release`."""
        while True:
            self.new_release = await check_for_releases()
            if self.new_release:
                log.info("#" * 60)
                log.info(format_release(self.new_release))
                log.info("#" * 60)
            await asyncio.sleep(86400)  # 24 hrs

    def vacuum_bans(self):
        """remove any bans that might have expired. This takes a while, so it is
        split up over the event loop"""

        def do_vacuum_bans():
            """do the actual clearing of bans"""

            bans_count = len(self.bans)
            log.info("starting ban vacuum with {count} bans",
                     count=bans_count)
            start_time = time.time()

            # create a copy of the items, so we don't have issues modifying
            # while iteraing
            for ban in list(self.bans.iteritems()):
                ban_exipry = ban[1][2]
                if ban_exipry is None:
                    # entry never expires
                    continue
                if ban[1][2] < start_time:
                    # expired
                    del self.bans[ban[0]]
                yield
            log.debug("ban vacuum took {time:.2f} seconds, removed {count} bans",
                      count=bans_count - len(self.bans),
                      time=time.time() - start_time)
            self.save_bans()

        # TODO: use cooperate() here instead, once you figure out why it's
        # swallowing errors. Perhaps try add an errback?
        coiterate(do_vacuum_bans())

    def undo_last_ban(self):
        result = self.bans.pop()
        self.save_bans()
        return result

    def save_bans(self):
        ban_file = os.path.join(config.config_dir, bans_file.get())
        ensure_dir_exists(ban_file)

        start_time = reactor.seconds()
        with open(ban_file, 'w') as f:
            json.dump(self.bans.make_list(), f, indent=2)
        log.debug("saving {count} bans took {time:.2f} seconds",
                  count=len(self.bans),
                  time=reactor.seconds() - start_time)

        if self.ban_publish is not None:
            self.ban_publish.update()

    def receive_callback(self, address: Address, data: bytes) -> int:
        """This hook receives the raw UDP data before it is processed by enet"""

        # exceptions get swallowed in the pyenet C stuff, so we catch anything
        # for now. This should ideally get fixed in pyenet instead.
        try:
            # reply to ASCII HELLO messages with HI so that clients can measure the
            # connection latency
            if data == b'HELLO':
                self.host.socket.send(address, b'HI')
                return 1
            # reply to ASCII HELLOLAN messages with server data for LAN discovery
            elif data == b'HELLOLAN':
                # we might receive a HELLOLAN before the map has been loaded
                # if so, return a dummy string instead
                if self.map_info:
                    map_name = self.map_info.short_name
                else:
                    map_name = "loading..."
                entry = {
                    "name": self.name,
                    "players_current": self.get_player_count(),
                    "players_max": self.max_players,
                    "map": map_name,
                    "game_mode": self.get_mode_name(),
                    "game_version": "0.75"
                }
                payload = json.dumps(entry).encode()
                self.host.socket.send(address, payload)
                return 1

            # This drop the connection of any ip in hard_bans
            if address.host in self.hard_bans:
                return 1
        except Exception:
            import traceback
            traceback.print_exc()

        return 0

    def data_received(self, peer: Peer, packet: Packet) -> None:
        ip = peer.address.host
        current_time = reactor.seconds()
        try:
            ServerProtocol.data_received(self, peer, packet)
        except (NoDataLeft, ValueError):
            import traceback
            traceback.print_exc()
            log.info(
                'IP %s was hardbanned for invalid data or possibly DDoS.' % ip)
            self.hard_bans.add(ip)
            return
        dt = reactor.seconds() - current_time
        if dt > 1.0:
            log.warn('processing {!r} from {} took {}'.format(
                packet.data, ip, dt))

    def irc_say(self, msg: str, me: bool = False) -> None:
        if self.irc_relay:
            if me:
                self.irc_relay.me(msg, do_filter=True)
            else:
                self.irc_relay.send(msg, do_filter=True)

    def send_tip(self):
        line = self.tips[random.randrange(len(self.tips))]
        self.send_chat(line)
        reactor.callLater(self.tip_frequency * 60, self.send_tip)

    # pylint: disable=arguments-differ
    def broadcast_chat(self, value, global_message=True, sender=None,
                       team=None, irc=False):
        """
        Send a chat message to many users
        """
        if irc:
            self.irc_say('* %s' % value)
        ServerProtocol.send_chat(self, value, global_message, sender, team)

    # backwards compatability
    send_chat = broadcast_chat

    # log high CPU usage

    def update_world(self):
        last_time = self.last_time
        current_time = reactor.seconds()
        if last_time is not None:
            dt = current_time - last_time
            if dt > 1.0:
                log.warn('high CPU usage detected - %s' % dt)
        self.last_time = current_time
        ServerProtocol.update_world(self)
        time_taken = reactor.seconds() - current_time
        if time_taken > 1.0:
            log.warn(
                'World update iteration took %s, objects: %s' %
                (time_taken, self.world.objects))

    # events

    def on_map_change(self, the_map: VXLData) -> None:
        self.set_fog_color(
            getattr(self.map_info.info, 'fog', self.default_fog)
        )

        map_on_map_change = self.map_info.on_map_change
        if map_on_map_change is not None:
            map_on_map_change(self, the_map)

    def on_map_leave(self):
        map_on_map_leave = self.map_info.on_map_leave
        if map_on_map_leave is not None:
            map_on_map_leave(self)

    def on_game_end(self):
        if self.advance_on_win <= 0:
            self.irc_say('Round ended!', me=True)
        elif next(self.win_count) % self.advance_on_win == 0:
            self.advance_rotation('Game finished!')

    def on_advance(self, map_name: str) -> None:
        pass

    def on_ban_attempt(self, connection, reason, duration):
        return True

    def on_ban(self, connection, reason, duration):
        pass

    # voting

    def cancel_vote(self, connection=None):
        return 'No vote in progress.'

    # useful twisted wrappers

    def listenTCP(self, *arg, **kw) -> Port:
        return reactor.listenTCP(
            *arg, interface=network_interface.get(), **kw)

    def connectTCP(self, *arg, **kw):
        return reactor.connectTCP(
            *arg,
            bindAddress=(
                network_interface.get(),
                0),
            **kw)

    # before-end calls

    def call_end(self, delay: int, func: Callable, *arg, **kw) -> EndCall:
        call = EndCall(self, delay, func, *arg, **kw)
        call.set(self.get_advance_time())
        return call

    def get_advance_time(self) -> float:
        if not self.advance_call:
            return None
        return self.advance_call.getTime() - self.advance_call.seconds()


def run() -> None:
    """
    runs the server
    """

    # load and apply regular scripts
    script_names = scripts_option.get()
    script_dir = os.path.join(config.config_dir, 'scripts/')
    script_objects = extensions.load_scripts_regular_extension(
        script_names, script_dir)
    (protocol_class, connection_class) = extensions.apply_scripts(
        script_objects, config, FeatureProtocol, FeatureConnection)

    # load and apply the game_mode script
    game_mode_name = game_mode.get()
    game_mode_dir = os.path.join(config.config_dir, 'game_modes/')
    game_mode_object = extensions.load_script_game_mode(
        game_mode_name, game_mode_dir)
    (protocol_class, connection_class) = extensions.apply_scripts(
        game_mode_object, config, protocol_class, connection_class)

    protocol_class.connection_class = connection_class

    interface = network_interface.get().encode('utf-8')

    # instantiate the protocol class once. It will set timers and hooks to keep
    # itself running once we start the reactor
    protocol_class(interface, config.get_dict())

    log.debug('Checking for unregistered config items...')
    unused = config.check_unused()
    if unused:
        log.warn('The following config items are not used:')
        pprint(unused)

    log.info('Started server...')

    profile = logging_profile_option.get()
    if profile:
        import cProfile
        cProfile.runctx('reactor.run()', None, globals())
    else:
        reactor.run()
