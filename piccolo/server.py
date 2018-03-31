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
import sys
import os
import imp
import importlib
import json
import itertools
import random
import time
from collections import deque
from pprint import pprint
from ipaddress import ip_network, ip_address, IPv4Address, AddressValueError
from typing import Any, Callable, Dict, Iterator, List, Optional, Tuple


from twisted.internet import reactor
from twisted.internet.defer import inlineCallbacks
from twisted.python import log
from twisted.python.logfile import DailyLogFile
from twisted.web import client as web_client
from twisted.internet.tcp import Port
from twisted.internet.defer import Deferred

from enet import Address, Packet, Peer


import pyspades.debug
from pyspades.server import (ServerProtocol, Team)
from pyspades.common import encode
from pyspades.constants import (CTF_MODE, TC_MODE)
from pyspades.master import MAX_SERVER_NAME_SIZE
from pyspades.tools import make_server_identifier
from pyspades.bytes import NoDataLeft
from pyspades.vxl import VXLData

import piccolo
from piccolo.scheduler import Scheduler
from piccolo import commands
from piccolo.map import Map, MapNotFound, check_rotation, RotationInfo
from piccolo.console import create_console
from piccolo.networkdict import NetworkDict
from piccolo.player import FeatureConnection
from piccolo.config import config

# won't be used; just need to be executed
import piccolo.core_commands


def check_scripts(scripts):
    '''
    Checks if scripts were included multiple times.
    '''
    seen = set()
    dups = []
    for script in scripts:
        if script in seen:
            dups.append(script)
        else:
            seen.add(script)
    if dups:
        print("Scripts included multiple times: {}".format(dups))
        return False
    return True


# declare configuration options
bans_config = config.section('bans')
logging_config = config.section('logging')
team1_config = config.section('team1')
team2_config = config.section('team2')

bans_file = bans_config.option('file', default='bans.txt')
respawn_time_option = config.option('respawn_time', default=8)
respawn_waves = config.option('respawn_waves', default=False)
game_mode = config.option('game_mode', default='ctf')
random_rotation = config.option('random_rotation', default=False)
passwords = config.option('passwords', default={})
logfile = logging_config.option('logfile', default='./logs/log.txt')
map_rotation = config.option('rotation', default=['classicgen', 'random'],
                             validate=lambda x: isinstance(x, list))
default_time_limit = config.option(
    'default_time_limit', default=20,
    validate=lambda x: isinstance(x, (int, float)))
cap_limit = config.option('cap_limit', default=10,
                          validate=lambda x: isinstance(x, (int, float)))
advance_on_win = config.option('advance_on_win', default=False,
                               validate=lambda x: isinstance(x, bool))
team1_name = team1_config.option('name', default='Blue')
team2_name = team2_config.option('name', default='Green')
team1_color = team1_config.option('color', default=(0, 0, 196))
team2_color = team2_config.option('color', default=(0, 196, 0))
friendly_fire = config.option('friendly_fire', default=False)
friendly_fire_on_grief = config.option('friendly_fire_on_grief',
        default=True)
grief_friendly_fire_time = config.option('grief_friendly_fire_time',
        default=2)
spade_teamkills_on_grief = config.option('spade_teamkills_on_grief',
        default=False)
time_announcements = config.option('time_announcements', default=[1, 2, 3, 4, 5, 6, 7, 8, 9, 10,
                                              30, 60, 120, 180, 240, 300, 600,
                                              900, 1200, 1800, 2400, 3000])
rights = config.option('rights', default={})
port_option = config.option('port', default=32887, validate=lambda n: type(n) == int)
fall_damage = config.option('fall_damage', default=True)
teamswitch_interval = config.option('teamswitch_interval', default=0)
teamswitch_allowed = config.option('teamswitch_allowed', default=True)
max_players = config.option('max_players', default=20)
melee_damage = config.option('melee_damage', default=100)
max_connections_per_ip = config.option('max_connections_per_ip', default=0)
server_prefix = config.option('server_prefix', default='[*]')
balanced_teams = config.option('balanced_teams', default=None)
login_retries = config.option('login_retries', 1)
default_ban_duration = bans_config.option('default_duration', default=24 * 60)
speedhack_detect = config.option('speedhack_detect', True)
user_blocks_only = config.option('user_blocks_only', False)
debug_log_enabled = logging_config.option('debug_log', False)
logging_profile_option = logging_config.option('profile', False)
set_god_build = config.option('set_god_build', False)
ssh_enabled = config.section('ssh').option('enabled', False)
irc_options = config.option('irc', {})
status_server_enabled = config.section('status_server').option('enabled', False)
ban_publish = bans_config.option('publish', False)
ban_publish_port = bans_config.option('publish_port', 32885)
logging_rotate_daily = logging_config.option('rotate_daily', False)
tip_frequency = config.option('tips_frequency', 0)
register_master_option = config.option('master', False)

# default to http for ip_getter on windows
# see https://github.com/piccolo/piccolo/issues/215
if sys.platform == 'win32':
    default_ip_getter = 'http://services.buildandshoot.com/getip'
else:
    default_ip_getter = 'https://services.buildandshoot.com/getip'
ip_getter_option = config.option('ip_getter', default_ip_getter)
name_option = config.option('name', default='piccolo #%s' % random.randrange(0, 2000))
motd_option = config.option('motd')
help_option = config.option('help')
rules_option = config.option('rules')
tips_option = config.option('tips')
network_interface = config.option('network_interface', default='')
scripts_option = config.option('scripts', default=[], validate=check_scripts)
ban_subscribe_enabled = bans_config.option('subscribe', False)

web_client._HTTP11ClientFactory.noisy = False


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


class EndCall(object):
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
                self.call.reset(value)
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

    server_version = '%s - %s' % (sys.platform, piccolo.__version__)

    default_fog = (128, 232, 255)

    def __init__(self, interface: bytes, config_dict: Dict[str, Any]) -> None:
        self.config = config_dict
        if random_rotation:
            self.map_rotator_type = random_choice_cycle
        else:
            self.map_rotator_type = itertools.cycle  # pylint: disable=redefined-variable-type
        self.default_time_limit = default_time_limit.get()
        self.default_cap_limit = cap_limit.get()
        self.advance_on_win = int(advance_on_win.get())
        self.win_count = itertools.count(1)
        self.bans = NetworkDict()

        # attempt to load a saved bans list
        try:
            with open(os.path.join(config.config_dir, bans_file.get()), 'r') as f:
                self.bans.read_list(json.load(f))
        except FileNotFoundError:
            pass
        except IOError as e:
            print('Could not read bans.txt: {}'.format(e))
        except ValueError as e:
            print('Could not parse bans.txt: {}'.format(e))

        self.hard_bans = set()  # possible DDoS'ers are added here
        self.player_memory = deque(maxlen=100)
        if len(self.name) > MAX_SERVER_NAME_SIZE:
            print('(server name too long; it will be truncated to "%s")' % (
                self.name[:MAX_SERVER_NAME_SIZE]))
        self.respawn_time = respawn_time_option.get()
        self.respawn_waves = respawn_waves.get()
        if game_mode.get() == 'ctf':
            self.game_mode = CTF_MODE
        elif game_mode.get() == 'tc':
            self.game_mode = TC_MODE
        elif self.game_mode is None:
            raise NotImplementedError('invalid game mode: %s' % game_mode)
        self.game_mode_name = game_mode.get().split('.')[-1]
        self.team1_name = team1_name.get()
        self.team2_name = team2_name.get()
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
        if user_blocks_only.get():
            self.user_blocks = set()
        self.set_god_build = set_god_build.get()
        self.debug_log = debug_log_enabled.get()
        if self.debug_log:
            # TODO: make this configurable
            pyspades.debug.open_debug_log(
                os.path.join(config.config_dir, 'debug.log'))
        if ssh_enabled.get():
            from piccolo.ssh import RemoteConsole
            self.remote_console = RemoteConsole(self)
        irc = irc_options.get()
        if irc.get('enabled', False):
            from piccolo.irc import IRCRelay
            self.irc_relay = IRCRelay(self, irc)
        if status_server_enabled.get():
            from piccolo.statusserver import StatusServerFactory
            self.status_server = StatusServerFactory(self)
        if ban_publish.get():
            from piccolo.banpublish import PublishServer
            self.ban_publish = PublishServer(self, ban_publish_port.get())
        if ban_subscribe_enabled.get():
            from piccolo import bansubscribe
            self.ban_manager = bansubscribe.BanManager(self)
        # logfile path relative to config dir if not abs path
        l = logfile.get()
        if l.strip():  # catches empty filename
            if not os.path.isabs(l):
                l = os.path.join(config.config_dir, l)
            ensure_dir_exists(l)
            if logging_rotate_daily.get():
                logging_file = DailyLogFile(l, '.')
            else:
                logging_file = open(l, 'a')
            log.addObserver(log.FileLogObserver(logging_file).emit)
            log.msg('pyspades server started on %s' % time.strftime('%c'))
        log.startLogging(sys.stdout)  # force twisted logging

        self.start_time = reactor.seconds()
        self.end_calls = []
        # TODO: why is this here?
        create_console(self)

        for user_type, func_names in rights.get().items():
            for func_name in func_names:
                commands.add_rights(user_type, func_name)

        port = self.port = port_option.get()
        ServerProtocol.__init__(self, port, interface)
        self.host.intercept = self.receive_callback
        try:
            self.set_map_rotation(self.config['rotation'])
        except MapNotFound as e:
            print('Invalid map in map rotation (%s), exiting.' % e.map)
            raise SystemExit

        self.update_format()
        self.tip_frequency = tip_frequency.get()
        if self.tips is not None and self.tip_frequency > 0:
            reactor.callLater(self.tip_frequency * 60, self.send_tip)

        self.master = register_master_option.get()
        self.set_master()

        self.http_agent = web_client.Agent(reactor)

        ip_getter = ip_getter_option.get()
        if ip_getter:
            self.get_external_ip(ip_getter)

    @inlineCallbacks
    def get_external_ip(self, ip_getter: str) -> Iterator[Deferred]:
        print('Retrieving external IP from {!r} to generate server identifier.'.format(ip_getter))
        try:
            ip = yield self.getPage(ip_getter)
            ip = IPv4Address(ip.strip())
        except AddressValueError as e:
            print('External IP getter service returned invalid data.\n'
                  'Please check the "ip_getter" setting in your config.')
            return
        except Exception as e:
            print("Getting external IP failed:", e)
            return

        self.ip = ip
        self.identifier = make_server_identifier(ip, self.port)
        print('Server public ip address: {}:{}'.format(ip, self.port))
        print('Public aos identifier: {}'.format(self.identifier))

    def set_time_limit(self, time_limit: Optional[bool] = None, additive: bool=False) -> int:
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
            self.send_chat('%s minutes remaining.' %
                           int(round(remaining / 60)))

    def _time_up(self):
        self.advance_call = None
        self.advance_rotation('Time up!')

    def advance_rotation(self, message: None = None) -> None:
        """
        Advances to the next map in the rotation. If message is provided
        it will send it to the chat, waits for 10 seconds and then advances.
        """
        self.set_time_limit(False)
        if self.planned_map is None:
            self.planned_map = next(self.map_rotator)
        planned_map = self.planned_map
        self.planned_map = None
        self.on_advance(planned_map)
        if message is None:
            self.set_map_name(planned_map)
        else:
            self.send_chat(
                '%s Next map: %s.' % (message, planned_map.full_name),
                irc=True)
            reactor.callLater(10, self.set_map_name, planned_map)

    def get_mode_name(self) -> str:
        return self.game_mode_name

    def set_map_name(self, rot_info: RotationInfo) -> None:
        """
        Sets the map by its name.
        """
        map_info = self.get_map(rot_info)
        if self.map_info:
            self.on_map_leave()
        self.map_info = map_info
        self.max_score = self.map_info.cap_limit or self.default_cap_limit
        self.set_map(self.map_info.data)
        self.set_time_limit(self.map_info.time_limit)
        self.update_format()

    def get_map(self, rot_info: RotationInfo) -> Map:
        """
        Creates and returns a Map object from rotation info
        """
        return Map(rot_info, os.path.join(config.config_dir, 'maps'))

    def set_map_rotation(self, maps: List[str], now: bool = True) -> None:
        """
        Over-writes the current map rotation with provided one.
        And advances immediately with the new rotation by default.
        """
        maps = check_rotation(maps, os.path.join(config.config_dir, 'maps'))
        self.maps = maps
        self.map_rotator = self.map_rotator_type(maps)
        if now:
            self.advance_rotation()

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
        if extra is None:
            extra = {}

        map_info = self.map_info
        format_dict = {
            'map_name': map_info.name,
            'map_author': map_info.author,
            'map_description': map_info.description,
            'game_mode': self.get_mode_name()
        }
        format_dict.update(extra)
        return value % format_dict

    def format_lines(self, value: List[str]) -> List[str]:
        if value is None:
            return
        lines = []
        extra = {'server_name': self.name}
        for line in value:
            lines.append(self.format(line, extra))
        return lines

    def got_master_connection(self, client):
        print('Master connection established.')
        ServerProtocol.got_master_connection(self, client)

    def master_disconnected(self, client=None):
        ServerProtocol.master_disconnected(self, client)
        if self.master and self.master_reconnect_call is None:
            if client:
                message = 'Master connection could not be established'
            else:
                message = 'Master connection lost'
            print('%s, reconnecting in 60 seconds...' % message)
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

    def add_ban(self, ip, reason, duration, name=None):
        """
        Ban an ip with an optional reason and duration in minutes. If duration
        is None, ban is permanent.
        """
        network = ip_network(str(ip), strict=False)
        for connection in list(self.connections.values()):
            if ip_address(connection.address[0]) in network:
                name = connection.name
                connection.kick(silent=True)
        if duration:
            duration = reactor.seconds() + duration * 60
        else:
            duration = None
        self.bans[ip] = (name or '(unknown)', reason, duration)
        self.save_bans()

    def remove_ban(self, ip):
        results = self.bans.remove(ip)
        print('Removing ban:', ip, results)
        self.save_bans()

    def undo_last_ban(self):
        result = self.bans.pop()
        self.save_bans()
        return result

    def save_bans(self):
        ban_file = os.path.join(config.config_dir, 'bans.txt')
        ensure_dir_exists(ban_file)
        with open(ban_file, 'w') as f:
            json.dump(self.bans.make_list(), f, indent=2)
        if self.ban_publish is not None:
            self.ban_publish.update()

    def receive_callback(self, address: Address, data: bytes) -> None:
        """This hook recieves the raw UDP data before it is processed by enet"""

        # reply to ASCII HELLO messages with HI so that clients can measure the
        # connection latency
        if data == b'HELLO':
            self.host.socket.send(address, b'HI')
            return 1

        # This drop the connection of any ip in hard_bans
        if address.host in self.hard_bans:
            return 1

    def data_received(self, peer: Peer, packet: Packet) -> None:
        ip = peer.address.host
        current_time = reactor.seconds()
        try:
            ServerProtocol.data_received(self, peer, packet)
        except (NoDataLeft, ValueError):
            import traceback
            traceback.print_exc()
            print(
                'IP %s was hardbanned for invalid data or possibly DDoS.' % ip)
            self.hard_bans.add(ip)
            return
        dt = reactor.seconds() - current_time
        if dt > 1.0:
            print('(warning: processing %r from %s took %s)' % (
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
                print('(warning: high CPU usage detected - %s)' % dt)
        self.last_time = current_time
        ServerProtocol.update_world(self)
        time_taken = reactor.seconds() - current_time
        if time_taken > 1.0:
            print(
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

    @inlineCallbacks
    def getPage(self, url: str) -> Iterator[Deferred]:
        resp = yield self.http_agent.request(b'GET', url.encode())
        body = yield web_client.readBody(resp)
        return body.decode()

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

    # apply scripts

    protocol_class = FeatureProtocol
    connection_class = FeatureConnection

    script_objects = []
    script_names = scripts_option.get()
    script_dir = os.path.join(config.config_dir, 'scripts/')

    for script in script_names[:]:
        try:
            # this finds and loads scripts directly from the script dir
            # no need for messing with sys.path
            f, filename, desc = imp.find_module(script, [script_dir])
            module = imp.load_module('piccolo_script_namespace_' + script, f, filename, desc)
            script_objects.append(module)
        except ImportError as e:
            # warning: this also catches import errors from inside the script
            # module it tried to load
            try:
                module = importlib.import_module(script)
                script_objects.append(module)
            except ImportError as e:
                print("(script '%s' not found: %r)" % (script, e))
                script_names.remove(script)

    for script in script_objects:
        protocol_class, connection_class = script.apply_script(
            protocol_class, connection_class, config.get_dict())

    # apply the game_mode script
    if game_mode.get() not in ('ctf', 'tc'):
        # must be a script with this game mode
        module = None
        try:
            game_mode_dir = os.path.join(config.config_dir, 'game_modes/')
            f, filename, desc = imp.find_module(game_mode.get(), [game_mode_dir])
            module = imp.load_module('piccolo_gamemode_namespace_' + game_mode.get(), f, filename, desc)
        except ImportError as e:
            try:
                module = importlib.import_module(game_mode.get())
            except ImportError as e:
                print("(game_mode '%s' not found: %r)" % (game_mode.get(), e))

        if module:
            protocol_class, connection_class = module.apply_script(
                protocol_class, connection_class, config.get_dict())

    protocol_class.connection_class = connection_class

    interface = network_interface.get().encode('utf-8')

    # TODO: is this required? Maybe protocol_class needs to be called?
    # either way, the resulting object is not used
    protocol_class(interface, config.get_dict())

    print('Checking for unregistered config items...')
    unused = config.check_unused()
    if unused:
        print('The following config items are not used:')
        pprint(unused)

    print('Started server...')

    profile = logging_profile_option.get()
    if profile:
        import cProfile
        cProfile.runctx('reactor.run()', None, globals())
    else:
        reactor.run()
