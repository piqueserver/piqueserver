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
from __future__ import print_function, unicode_literals
import sys
import os
import errno
import imp
import importlib
import json
import itertools
import random
import time
from collections import deque

import six
from six import text_type
from six.moves import range

from ipaddress import ip_network, ip_address, IPv4Address, AddressValueError
from twisted.internet import reactor
from twisted.internet.defer import inlineCallbacks, returnValue
from twisted.python import log
from twisted.python.logfile import DailyLogFile
from twisted.web import client as web_client

from piqueserver import cfg
from piqueserver.config import config as config_store

import pyspades.debug
from pyspades.server import (ServerProtocol, Team)
from pyspades.common import encode
from pyspades.constants import (CTF_MODE, TC_MODE)
from pyspades.master import MAX_SERVER_NAME_SIZE
from pyspades.tools import make_server_identifier
from pyspades.bytes import NoDataLeft

from piqueserver.scheduler import Scheduler
from piqueserver import commands
from piqueserver.map import Map, MapNotFound, check_rotation
from piqueserver.console import create_console
from piqueserver.networkdict import NetworkDict
from piqueserver.player import FeatureConnection

# won't be used; just need to be executed
import piqueserver.core_commands

def check_passwords(passwords):
    '''
    Validator function to be run when the passwords configuration item is updated/set.
    Designed to warn if default passwords found in the config.
    '''
    # default passwords as hardcoded in example config
    default_passwords = {
        'admin': ['adminpass1', 'adminpass2', 'adminpass3'],
        'moderator': ['modpass'],
        'guard': ['guardpass'],
        'trusted': ['trustedpass']
    }

    # check for default password usage
    for group, passwords in passwords.items():
        if group in default_passwords:
            for password in passwords:
                if password in default_passwords[group]:
                    print(("WARNING: FOUND DEFAULT PASSWORD '%s'"
                           " IN GROUP '%s'" % (password, group)))

    # always validate - this function is just to warn if default passwords found
    return True


PORT = 32887

web_client._HTTP11ClientFactory.noisy = False

def ensure_dir_exists(filename):
    d = os.path.dirname(filename)
    try:
        os.makedirs(d)
    except OSError as e:
        if e.errno == errno.EEXIST:
            pass
        else:
            raise e

def random_choice_cycle(choices):
    while True:
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
    _active = True

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
        self._active = False

    def active(self):
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

    server_version = cfg.server_version

    default_fog = (128, 232, 255)

    def __init__(self, interface, config):
        self.config = config
        if config.get('random_rotation', False):
            self.map_rotator_type = random_choice_cycle
        else:
            self.map_rotator_type = itertools.cycle  # pylint: disable=redefined-variable-type
        self.default_time_limit = config.get('default_time_limit', 20.0)
        self.default_cap_limit = config.get('cap_limit', 10.0)
        self.advance_on_win = int(config.get('advance_on_win', False))
        self.win_count = itertools.count(1)
        self.bans = NetworkDict()

        # attempt to load a saved bans list
        try:
            with open(os.path.join(cfg.config_dir, 'bans.txt'), 'r') as f:
                self.bans.read_list(json.load(f))
        except OSError as e:
            if e.errno == errno.ENOENT:
                # if it doesn't exist, then no bans, no error
                pass
            else:
                raise e
        except IOError as e:
            print('Could not read bans.txt: {}'.format(e))
        except ValueError as e:
            print('Could not parse bans.txt: {}'.format(e))

        self.hard_bans = set()  # possible DDoS'ers are added here
        self.player_memory = deque(maxlen=100)
        self.config = config
        if len(self.name) > MAX_SERVER_NAME_SIZE:
            print('(server name too long; it will be truncated to "%s")' % (
                self.name[:MAX_SERVER_NAME_SIZE]))
        self.respawn_time = config.get('respawn_time', 8)
        self.respawn_waves = config.get('respawn_waves', False)
        game_mode = config.get('game_mode', 'ctf')
        if game_mode == 'ctf':
            self.game_mode = CTF_MODE
        elif game_mode == 'tc':
            self.game_mode = TC_MODE
        elif self.game_mode is None:
            raise NotImplementedError('invalid game mode: %s' % game_mode)
        self.game_mode_name = game_mode.split('.')[-1]
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
        self.passwords = config_store.option('passwords', default={}, validate=check_passwords).get()
        self.server_prefix = config.get('server_prefix', '[*]')
        self.time_announcements = config.get('time_announcements',
                                             [1, 2, 3, 4, 5, 6, 7, 8, 9, 10,
                                              30, 60, 120, 180, 240, 300, 600,
                                              900, 1200, 1800, 2400, 3000])
        self.balanced_teams = config.get('balanced_teams', None)
        self.login_retries = config.get('login_retries', 1)

        # voting configuration
        self.default_ban_time = config.get('default_ban_duration', 24 * 60)

        self.speedhack_detect = config.get('speedhack_detect', True)
        if config.get('user_blocks_only', False):
            self.user_blocks = set()
        self.set_god_build = config.get('set_god_build', False)
        self.debug_log = config.get('debug_log', False)
        if self.debug_log:
            pyspades.debug.open_debug_log(
                os.path.join(cfg.config_dir, 'debug.log'))
        ssh = config.get('ssh', {})
        if ssh.get('enabled', False):
            from piqueserver.ssh import RemoteConsole
            self.remote_console = RemoteConsole(self, ssh)
        irc = config.get('irc', {})
        if irc.get('enabled', False):
            from piqueserver.irc import IRCRelay
            self.irc_relay = IRCRelay(self, irc)
        status = config.get('status_server', {})
        if status.get('enabled', False):
            from piqueserver.statusserver import StatusServerFactory
            self.status_server = StatusServerFactory(self, status)
        publish = config.get('ban_publish', {})
        if publish.get('enabled', False):
            from piqueserver.banpublish import PublishServer
            self.ban_publish = PublishServer(self, publish)
        ban_subscribe = config.get('ban_subscribe', {})
        if ban_subscribe.get('enabled', True):
            from piqueserver import bansubscribe
            self.ban_manager = bansubscribe.BanManager(self, ban_subscribe)
        # logfile path relative to config dir if not abs path
        logfile = config.get('logfile', '')
        if not os.path.isabs(logfile):
            logfile = os.path.join(cfg.config_dir, logfile)
        if logfile.strip():  # catches empty filename
            ensure_dir_exists(logfile)
            if config.get('rotate_daily', False):
                logging_file = DailyLogFile(logfile, '.')
            else:
                logging_file = open(logfile, 'a')
            log.addObserver(log.FileLogObserver(logging_file).emit)
            log.msg('pyspades server started on %s' % time.strftime('%c'))
        log.startLogging(sys.stdout)  # force twisted logging

        self.start_time = reactor.seconds()
        self.end_calls = []
        # TODO: why is this here?
        create_console(self)

        for password in self.passwords.get('admin', []):
            if not password:
                self.everyone_is_admin = True

        for user_type, func_names in config.get('rights', {}).items():
            for func_name in func_names:
                commands.add_rights(user_type, func_name)

        port = self.port = config.get('port', 32887)
        ServerProtocol.__init__(self, port, interface)
        self.host.intercept = self.receive_callback
        try:
            self.set_map_rotation(config['maps'])
        except MapNotFound as e:
            print('Invalid map in map rotation (%s), exiting.' % e.map)
            raise SystemExit

        self.update_format()
        self.tip_frequency = config.get('tip_frequency', 0)
        if self.tips is not None and self.tip_frequency > 0:
            reactor.callLater(self.tip_frequency * 60, self.send_tip)

        self.master = config.get('master', True)
        self.set_master()

        self.http_agent = web_client.Agent(reactor)

        # ip_getter should be a url that returns only the requester's public ip in the response body
        # other tools:
        # https://icanhazip.com/
        # https://api.ipify.org
        #
        # default to http on windows - see https://github.com/piqueserver/piqueserver/issues/215
        if sys.platform == 'win32':
            default_ip_getter = 'http://services.buildandshoot.com/getip'
        else:
            default_ip_getter = 'https://services.buildandshoot.com/getip'

        ip_getter = config.get('ip_getter', default_ip_getter)
        if ip_getter:
            self.get_external_ip(ip_getter)

    @inlineCallbacks
    def get_external_ip(self, ip_getter):
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

    def set_time_limit(self, time_limit=None, additive=False):
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

    def advance_rotation(self, message=None):
        """
        Advances to the next map in the rotation. If message is provided
        it will send it to the chat, waits for 10 seconds and then advances.
        """
        self.set_time_limit(False)
        if self.planned_map is None:
            self.planned_map = next(self.map_rotator)
        planned_map = self.planned_map
        self.planned_map = None
        self.on_advance(map)
        if message is None:
            self.set_map_name(planned_map)
        else:
            self.send_chat(
                '%s Next map: %s.' % (message, planned_map.full_name),
                irc=True)
            reactor.callLater(10, self.set_map_name, planned_map)

    def get_mode_name(self):
        return self.game_mode_name

    def set_map_name(self, rot_info):
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

    def get_map(self, rot_info):
        """
        Creates and returns a Map object from rotation info
        """
        return Map(rot_info, os.path.join(cfg.config_dir, 'maps'))

    def set_map_rotation(self, maps, now=True):
        """
        Over-writes the current map rotation with provided one.
        And advances immediately with the new rotation by default.
        """
        maps = check_rotation(maps, os.path.join(cfg.config_dir, 'maps'))
        self.maps = maps
        self.map_rotator = self.map_rotator_type(maps)
        if now:
            self.advance_rotation()

    def get_map_rotation(self):
        return [map_item.full_name for map_item in self.maps]

    def is_indestructable(self, x, y, z):
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

    def update_format(self):
        """
        Called when the map (or other variables) have been updated
        """
        config = self.config
        default_name = 'pyspades server %s' % random.randrange(0, 2000)
        self.name = self.format(config.get('name', default_name))
        self.motd = self.format_lines(config.get('motd', None))
        self.help = self.format_lines(config.get('help', None))
        self.tips = self.format_lines(config.get('tips', None))
        self.rules = self.format_lines(config.get('rules', None))
        if self.master_connection is not None:
            self.master_connection.send_server()

    def format(self, value, extra=None):
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

    def format_lines(self, value):
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
        network = ip_network(text_type(ip), strict=False)
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
        ban_file = os.path.join(cfg.config_dir, 'bans.txt')
        ensure_dir_exists(ban_file)
        with open(ban_file, 'w') as f:
            json.dump(self.bans.make_list(), f, indent=2)
        if self.ban_publish is not None:
            self.ban_publish.update()

    def receive_callback(self, address, data):
        """This hook recieves the raw UDP data before it is processed by enet"""

        # reply to ASCII HELLO messages with HI so that clients can measure the
        # connection latency
        if data == b'HELLO':
            self.host.socket.send(address, b'HI')
            return 1

        # This drop the connection of any ip in hard_bans
        if address.host in self.hard_bans:
            return 1

    def data_received(self, peer, packet):
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

    def irc_say(self, msg, me=False):
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

    def on_map_change(self, the_map):
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

    def on_advance(self, map_name):
        pass

    def on_ban_attempt(self, connection, reason, duration):
        return True

    def on_ban(self, connection, reason, duration):
        pass

    # voting

    def cancel_vote(self, connection=None):
        return 'No vote in progress.'

    # useful twisted wrappers

    def listenTCP(self, *arg, **kw):
        return reactor.listenTCP(
            *arg, interface=self.config.get('network_interface', ''), **kw)

    def connectTCP(self, *arg, **kw):
        return reactor.connectTCP(
            *arg,
            bindAddress=(
                self.config.get(
                    'network_interface',
                    ''),
                0),
            **kw)

    @inlineCallbacks
    def getPage(self, url):
        resp = yield self.http_agent.request(b'GET', url.encode())
        body = yield web_client.readBody(resp)
        returnValue(body.decode())

    # before-end calls

    def call_end(self, delay, func, *arg, **kw):
        call = EndCall(self, delay, func, *arg, **kw)
        call.set(self.get_advance_time())
        return call

    def get_advance_time(self):
        if not self.advance_call:
            return None
        return self.advance_call.getTime() - self.advance_call.seconds()


def run():
    """
    runs the server
    """

    try:
        with open(cfg.config_file, 'r') as f:
            config = json.load(f)
            cfg.config = config
    except IOError as e:
        print(
            'Error reading config from {} - {}: '.format(cfg.config_file, e))
        print('If you haven\'t already, try copying the example config to '
              'the default location with "piqueserver --copy-config".')
        sys.exit(1)
    except ValueError as e:
        print("Error in config file {}: ".format(cfg.config_file) + str(e))
        sys.exit(1)

    # update with parameters from cfg (supplied as cli args)
    if cfg.json_parameters:
        try:
            params = json.loads(cfg.json_parameters)
        except Exception as e:  # pylint: disable=broad-except
            print('Error loading json parameters from the command line')
            print(e)
            sys.exit(1)
        config.update(params)

    # apply scripts

    protocol_class = FeatureProtocol
    connection_class = FeatureConnection

    script_objects = []
    script_names = config.get('scripts', [])
    script_dir = os.path.join(cfg.config_dir, 'scripts/')

    for script in script_names[:]:
        try:
            # this finds and loads scripts directly from the script dir
            # no need for messing with sys.path
            f, filename, desc = imp.find_module(script, [script_dir])
            module = imp.load_module('piqueserver_script_namespace_' + script, f, filename, desc)
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
            protocol_class, connection_class, config)


    # apply the game_mode script
    game_mode = config.get('game_mode', 'ctf')
    if game_mode not in ('ctf', 'tc'):
        # must be a script with this game mode
        module = None
        try:
            game_mode_dir = os.path.join(cfg.config_dir, 'game_modes/')
            f, filename, desc = imp.find_module(game_mode, [game_mode_dir])
            module = imp.load_module('piqueserver_gamemode_namespace_' + game_mode, f, filename, desc)
        except ImportError as e:
            try:
                module = importlib.import_module(game_mode)
            except ImportError as e:
                print("(game_mode '%s' not found: %r)" % (game_mode, e))

        if module:
            protocol_class, connection_class = module.apply_script(
                protocol_class, connection_class, config)

    protocol_class.connection_class = connection_class

    interface = config.get('network_interface', '').encode('utf-8')

    # TODO: is this required? Maybe protocol_class needs to be called?
    # either way, the resulting object is not used
    protocol_class(interface, config)

    print('Started server...')

    profile = config.get('profile', False)
    if profile:
        import cProfile
        cProfile.runctx('reactor.run()', None, globals())
    else:
        reactor.run()
