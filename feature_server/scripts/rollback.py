"""
Progressively roll backs map to their original state (or to another map).

Maintainer: hompy
"""

from twisted.internet.task import LoopingCall
from pyspades.vxl import VXLData
from pyspades.contained import BlockAction, SetColor
from pyspades.constants import *
from pyspades.common import coordinates, make_color
from map import Map, MapNotFound, check_rotation
from commands import add, admin
import time
import operator

S_INVALID_MAP_NAME = 'Invalid map name'
S_ROLLBACK_IN_PROGRESS = 'Rollback in progress'
S_ROLLBACK_COMMENCED = '{player} commenced a rollback...'
S_AUTOMATIC_ROLLBACK_PLAYER_NAME = 'Map'
S_NO_ROLLBACK_IN_PROGRESS = 'No rollback in progress'
S_ROLLBACK_CANCELLED = 'Rollback cancelled by {player}'
S_ROLLBACK_ENDED = 'Rollback ended. {result}'
S_MAP_CHANGED = 'Map was changed'
S_ROLLBACK_PROGRESS = 'Rollback progress {percent:.0%}'
S_ROLLBACK_COLOR_PASS = 'Rollback doing color pass...'
S_ROLLBACK_TIME_TAKEN = 'Time taken: {seconds:.3}s'

NON_SURFACE_COLOR = (0, 0, 0)

@admin
def rollmap(connection, mapname = None, value = None):
    start_x, start_y, end_x, end_y = 0, 0, 512, 512
    if value is not None:
        start_x, start_y = coordinates(value)
        end_x, end_y = start_x + 64, start_y + 64
    return connection.protocol.start_rollback(connection, mapname,
        start_x, start_y, end_x, end_y)

@admin
def rollback(connection, value = None):
    return rollmap(connection, value = value)

@admin
def rollbackcancel(connection):
    return connection.protocol.cancel_rollback(connection)

for func in (rollmap, rollback, rollbackcancel):
    add(func)

def apply_script(protocol, connection, config):
    rollback_on_game_end = config.get('rollback_on_game_end', False)

    class RollbackConnection(connection):
        def on_block_destroy(self, x, y, z, value):
            if self.protocol.rollback_in_progress:
                return False
            return connection.on_block_destroy(self, x, y, z, value)

    class RollbackProtocol(protocol):
        rollback_in_progress = False
        rollback_max_rows = 10 # per 'cycle', intended to cap cpu usage
        rollback_max_packets = 180 # per 'cycle' cap for (unique packets * players)
        rollback_max_unique_packets = 12 # per 'cycle', each block op is at least 1
        rollback_time_between_cycles = 0.06
        rollback_time_between_progress_updates = 10.0
        rollback_start_time = None
        rollback_last_chat = None
        rollback_rows = None
        rollback_total_rows = None

        # rollback

        def start_rollback(self, connection, mapname, start_x, start_y,
            end_x, end_y, ignore_indestructable = True):
            if self.rollback_in_progress:
                return S_ROLLBACK_IN_PROGRESS
            if mapname is None:
                map = self.rollback_map
            else:
                try:
                    maps = check_rotation([mapname])
                    if not maps:
                        return S_INVALID_MAP_NAME
                    map = Map(maps[0]).data
                except MapNotFound as error:
                    return error.message
            name = (connection.name if connection is not None
                else S_AUTOMATIC_ROLLBACK_PLAYER_NAME)
            message = S_ROLLBACK_COMMENCED.format(player = name)
            self.send_chat(message, irc = True)
            self.packet_generator = self.create_rollback_generator(self.map,
                map, start_x, start_y, end_x, end_y, ignore_indestructable)
            self.rollback_in_progress = True
            self.rollback_start_time = time.time()
            self.rollback_last_chat = self.rollback_start_time
            self.rollback_rows = 0
            self.rollback_total_rows = end_x - start_x
            self.cycle_call = LoopingCall(self.rollback_cycle)
            self.cycle_call.start(self.rollback_time_between_cycles)

        def cancel_rollback(self, connection):
            if not self.rollback_in_progress:
                return S_NO_ROLLBACK_IN_PROGRESS
            result = S_ROLLBACK_CANCELLED.format(player = connection.name)
            self.end_rollback(result)

        def end_rollback(self, result):
            self.rollback_in_progress = False
            self.cycle_call.stop()
            self.cycle_call = None
            self.packet_generator = None
            self.update_entities()
            message = S_ROLLBACK_ENDED.format(result = result)
            self.send_chat(message, irc = True)

        def rollback_cycle(self):
            if not self.rollback_in_progress:
                return
            try:
                sent_unique = sent_total = rows = 0
                while 1:
                    if rows > self.rollback_max_rows:
                        break
                    if sent_unique > self.rollback_max_unique_packets:
                        break
                    if sent_total > self.rollback_max_packets:
                        break
                    sent = self.packet_generator.next()
                    sent_unique += sent
                    sent_total += sent * len(self.connections)
                    rows += (sent == 0)
                self.rollback_rows += rows
                if (time.time() - self.rollback_last_chat >
                    self.rollback_time_between_progress_updates):
                    self.rollback_last_chat = time.time()
                    progress = float(self.rollback_rows) / self.rollback_total_rows
                    if progress < 1.0:
                        message = S_ROLLBACK_PROGRESS.format(percent = progress)
                        self.send_chat(message)
                    else:
                        self.send_chat(S_ROLLBACK_COLOR_PASS)
            except (StopIteration):
                elapsed = time.time() - self.rollback_start_time
                message = S_ROLLBACK_TIME_TAKEN.format(seconds = elapsed)
                self.end_rollback(message)

        def create_rollback_generator(self, cur, new, start_x, start_y,
            end_x, end_y, ignore_indestructable):
            surface = {}
            block_action = BlockAction()
            block_action.player_id = 31
            set_color = SetColor()
            set_color.value = make_color(*NON_SURFACE_COLOR)
            set_color.player_id = 31
            self.send_contained(set_color, save = True)
            old = cur.copy()
            check_protected = hasattr(protocol, 'protected')
            for x in xrange(start_x, end_x):
                block_action.x = x
                for y in xrange(start_y, end_y):
                    block_action.y = y
                    if check_protected and self.is_protected(x, y, 0):
                        continue
                    for z in xrange(63):
                        action = None
                        cur_solid = cur.get_solid(x, y, z)
                        new_solid = new.get_solid(x, y, z)
                        if cur_solid and not new_solid:
                            if (not ignore_indestructable and
                                self.is_indestructable(x, y, z)):
                                continue
                            else:
                                action = DESTROY_BLOCK
                                cur.remove_point(x, y, z)
                        elif new_solid:
                            new_is_surface = new.is_surface(x, y, z)
                            if new_is_surface:
                                new_color = new.get_color(x, y, z)
                            if not cur_solid and new_is_surface:
                                surface[(x, y, z)] = new_color
                            elif not cur_solid and not new_is_surface:
                                action = BUILD_BLOCK
                                cur.set_point(x, y, z, NON_SURFACE_COLOR)
                            elif cur_solid and new_is_surface:
                                old_is_surface = old.is_surface(x, y, z)
                                if old_is_surface:
                                    old_color = old.get_color(x, y, z)
                                if not old_is_surface or old_color != new_color:
                                    surface[(x, y, z)] = new_color
                                    action = DESTROY_BLOCK
                                    cur.remove_point(x, y, z)
                        if action is not None:
                            block_action.z = z
                            block_action.value = action
                            self.send_contained(block_action, save = True)
                            yield 1
                yield 0
            last_color = None
            block_action.value = BUILD_BLOCK
            for pos, color in sorted(surface.iteritems(),
                key = operator.itemgetter(1)):
                x, y, z = pos
                packets_sent = 0
                if color != last_color:
                    set_color.value = make_color(*color)
                    self.send_contained(set_color, save = True)
                    packets_sent += 1
                    last_color = color
                cur.set_point(x, y, z, color)
                block_action.x = x
                block_action.y = y
                block_action.z = z
                self.send_contained(block_action, save = True)
                packets_sent += 1
                yield packets_sent

        def on_map_change(self, map):
            self.rollback_map = map.copy()
            protocol.on_map_change(self, map)

        def on_map_leave(self):
            if self.rollback_in_progress:
                self.end_rollback(S_MAP_CHANGED)
            protocol.on_map_leave(self)

        def on_game_end(self):
            if rollback_on_game_end:
                self.start_rollback(None, None, 0, 0, 512, 512, False)
            protocol.on_game_end(self)

    return RollbackProtocol, RollbackConnection
