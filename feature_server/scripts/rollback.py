from map import Map
from commands import add, admin
from pyspades.common import coordinates
from pyspades.server import block_action, set_color
from twisted.internet import reactor
from pyspades.constants import *
import time

@admin
def rollmap(connection, filename = None, first_arg = None, second_arg = None):
    start_x, start_y, end_x, end_y, z_offset = 0, 0, 512, 512, 0
    if first_arg is not None and second_arg is None:
        try:
            start_x, start_y = coordinates(first_arg)
            end_x, end_y = start_x + 64, start_y + 64
        except (ValueError):
            z_offset = int(first_arg)
    elif first_arg is not None and second_arg is not None:
        start_x, start_y = coordinates(first_arg)
        end_x, end_y = start_x + 64, start_y + 64
        z_offset = int(second_arg)
    rollback_player = connection
    if connection not in connection.protocol.players:
        rollback_player = None
    return connection.protocol.start_rollback(rollback_player, filename,
        start_x, start_y, end_x, end_y, z_offset)

@admin
def rollback(connection, first_arg = None, second_arg = None):
    return rollmap(connection, first_arg = first_arg, second_arg = second_arg)

@admin
def rollbackcancel(connection):
    return connection.protocol.cancel_rollback(connection)

for func in (rollmap, rollback, rollbackcancel):
    add(func)

def apply_script(protocol, connection, config):
    rollback_on_game_end = config.get('rollback_on_game_end', False)
    rollback_map = Map.loaded_map.data
    
    class RollbackConnection(connection):
        def on_color_set(self, (r, g, b)):
            if (self.protocol.rollback_in_progress and
                self.protocol.rollbacking_player is self):
                return False
            
    class RollbackProtocol(protocol):
        rollback_in_progress = False
        rollback_max_rows = 10 # per 'cycle', intended to cap cpu usage
        rollback_max_packets = 180 # per 'cycle' cap for (unique packets * players)
        rollback_max_unique_packets = 12 # per 'cycle', each block op is at least 1
        rollback_time_between_cycles = 0.06
        rollback_time_between_progress_updates = 10.0
        rollbacking_player = None
        rollback_start_time = None
        rollback_last_chat = None
        rollback_rows = None
        rollback_total_rows = None
        
        # rollback
        
        def start_rollback(self, connection, filename,
                           start_x, start_y, end_x, end_y, z_offset):
            if self.rollback_in_progress:
                return 'Rollback in progress.'
            map = rollback_map if filename is None else Map(filename).data
            self.send_chat('%s commenced a rollback...' %
                (connection.name if connection is not None else 'Map'), irc = True)
            if connection is None:
                for player in self.players.values():
                    connection = player
                    if player.admin:
                        break
            packet_generator = self.create_rollback_generator(connection,
                self.map, map, start_x, start_y, end_x, end_y, z_offset)
            self.rollbacking_player = connection
            self.rollback_in_progress = True
            self.rollback_start_time = time.time()
            self.rollback_last_chat = self.rollback_start_time
            self.rollback_rows = 0
            self.rollback_total_rows = end_x - start_x
            self.rollback_cycle(packet_generator)
        
        def cancel_rollback(self, connection):
            if not self.rollback_in_progress:
                return 'No rollback in progress.'
            self.end_rollback('Cancelled by %s' % connection.name)
        
        def end_rollback(self, result):
            self.rollback_in_progress = False
            self.update_entities()
            self.send_chat('Rollback ended. %s' % result, irc = True)
        
        def rollback_cycle(self, packet_generator):
            if not self.rollback_in_progress:
                return
            try:
                sent = rows = 0
                while (True):
                    if rows > self.rollback_max_rows:
                        break
                    if sent > self.rollback_max_unique_packets:
                        break
                    if sent * len(self.connections) > self.rollback_max_packets:
                        break
                    
                    sent_packets = packet_generator.next()
                    sent += sent_packets
                    rows += (sent_packets == 0)
                self.rollback_rows += rows
                if (time.time() - self.rollback_last_chat >
                    self.rollback_time_between_progress_updates):
                    self.rollback_last_chat = time.time()
                    progress = (float(self.rollback_rows) /
                        self.rollback_total_rows * 100.0)
                    self.send_chat('Rollback progress %s%%' % int(progress))
            except (StopIteration):
                self.end_rollback('Time taken: %.2fs' % 
                    float(time.time() - self.rollback_start_time))
                return
            reactor.callLater(self.rollback_time_between_cycles,
                self.rollback_cycle, packet_generator)
        
        def create_rollback_generator(self, connection, mapdata, mapdata_new,
                                      start_x, start_y, end_x, end_y, z_offset):
            last_color = None
            for x in xrange(start_x, end_x):
                for y in xrange(start_y, end_y):
                    for z in xrange(63):
                        packets_sent = 0
                        block_action.value = None
                        old_solid = mapdata.get_solid(x, y, z)
                        new_solid = mapdata_new.get_solid(x, y, z + z_offset)
                        if old_solid and not new_solid:
                            block_action.value = DESTROY_BLOCK
                            mapdata.remove_point_unsafe(x, y, z)
                        elif not old_solid and new_solid:
                            block_action.value = BUILD_BLOCK
                            new_color = mapdata_new.get_color(x, y, z + z_offset)
                            set_color.value = new_color & 0xFFFFFF
                            set_color.player_id = connection.player_id
                            if new_color != last_color:
                                last_color = new_color
                                self.send_contained(set_color, save = True)
                                packets_sent += 1
                            mapdata.set_point_unsafe_int(x, y, z, new_color)
                        
                        if block_action.value is not None:
                            block_action.x = x
                            block_action.y = y
                            block_action.z = z
                            block_action.player_id = connection.player_id
                            self.send_contained(block_action, save = True)
                            packets_sent += 1
                            yield packets_sent
                yield 0
        
        def on_game_end(self, player):
            if rollback_on_game_end:
                self.start_rollback(None, None, 0, 0, 512, 512, 0)
        
    return RollbackProtocol, RollbackConnection